"""Celery tasks for email notifications."""
import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .certificate_utils import (
    build_frontend_certificate_url,
    build_frontend_journal_certificate_url,
    build_frontend_review_invite_url,
)
from .certificates import (
    build_journal_publication_certificate_pdf,
    build_reviewer_recognition_pdf,
)
from .sender import get_sender_header
from .models import (
    EmailLog,
    JournalPublicationCertificate,
    Notification,
    ReviewerRecognitionCertificate,
    STATUS_FAILED,
    STATUS_SENT,
)


logger = logging.getLogger(__name__)


def get_email_backend():
    """Return configured email backend."""
    use_provider = getattr(settings, "EMAIL_USE_PROVIDER", False)
    django_backend = getattr(settings, "EMAIL_BACKEND", "")

    # In tests/local debugging, locmem/console/file/dummy backends should bypass providers.
    provider_blocked_backends = {
        "django.core.mail.backends.locmem.EmailBackend",
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend",
        "django.core.mail.backends.dummy.EmailBackend",
    }

    if use_provider and django_backend not in provider_blocked_backends:
        from .backends.provider import ProviderBackend
        return ProviderBackend()
    from .backends.smtp import SMTPBackend
    return SMTPBackend()


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_notification_email(
    self,
    event_type: str,
    user_id: int | None,
    to_email: str,
    subject: str,
    body: str,
    payload: dict | None = None,
    idempotency_key: str | None = None,
):
    """
    Send notification email. Creates Notification and EmailLog records.
    Uses idempotency_key to avoid duplicate sends (e.g. for status_changed).
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    payload = payload or {}

    # Idempotency check for status_changed
    if idempotency_key:
        existing = Notification.objects.filter(
            event_type=event_type,
            idempotency_key=idempotency_key,
            status=STATUS_SENT,
        ).exists()
        if existing:
            return {"status": "skipped", "reason": "idempotent"}

    user = User.objects.filter(id=user_id).first() if user_id else None
    notification = Notification.objects.create(
        user=user,
        event_type=event_type,
        payload=payload,
        status="queued",
        idempotency_key=idempotency_key or "",
    )

    email_log = EmailLog.objects.create(
        to_email=to_email,
        subject=subject,
        body=body,
        status="queued",
    )

    try:
        html_message = None
        try:
            from .email_html import render_account_notification_html, wrap_email_html
            if event_type in {"email_verification", "profile_updated"}:
                html_message = render_account_notification_html(
                    subject=subject,
                    intro=body.splitlines()[2] if len(body.splitlines()) > 2 else body,
                    recipient_roles=payload.get("roles") if isinstance(payload, dict) else None,
                    changed_fields=payload.get("changed_fields") if isinstance(payload, dict) else None,
                    cta_label=("Verify email" if event_type == "email_verification" else "Open dashboard"),
                    cta_url=(
                        payload.get("verification_url")
                        if event_type == "email_verification"
                        else payload.get("dashboard_url")
                    )
                    if isinstance(payload, dict)
                    else None,
                )
            else:
                html_message = wrap_email_html(subject, body)
        except Exception:
            # Keep sending plain text even if HTML template code has issues.
            logger.exception("Failed to render HTML email; sending plain text")

        backend = get_email_backend()
        provider_msg_id = backend.send(to_email, subject, body, html_message=html_message)
        email_log.status = STATUS_SENT
        email_log.provider_message_id = provider_msg_id or ""
        email_log.save()
        notification.status = STATUS_SENT
        notification.sent_at = timezone.now()
        notification.save()
        return {"status": "sent", "notification_id": notification.id}
    except Exception as e:
        email_log.status = STATUS_FAILED
        email_log.error = str(e)
        email_log.save()
        notification.status = STATUS_FAILED
        notification.save()
        raise


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_review_reminder(self, assignment_id: int):
    """Send review reminder email to reviewer."""
    from reviews.models import ReviewAssignment

    assignment = ReviewAssignment.objects.filter(id=assignment_id).select_related(
        "submission"
    ).first()
    if not assignment:
        return {"status": "skipped", "reason": "assignment_not_found"}

    to_email = assignment.reviewer.email if assignment.reviewer else assignment.invited_email
    if not to_email:
        return {"status": "skipped", "reason": "no_email"}

    submission = assignment.submission
    subject = f"Reminder: Review due for submission - {submission.title[:50]}"
    invite_url = build_frontend_review_invite_url(assignment.token)
    body = f"""You have a pending review for the submission "{submission.title}".

Please submit your review by {assignment.due_date or 'the given deadline'}.

Open the invitation here: {invite_url}
"""

    return send_notification_email(
        event_type="review_reminder",
        user_id=assignment.reviewer_id,
        to_email=to_email,
        subject=subject,
        body=body,
        payload={"assignment_id": assignment_id, "submission_id": submission.id},
    )


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_author_reviewer_recognition_certificate(self, review_id: int):
    """Generate reviewer recognition PDF and email it to author after editor accepts."""
    from reviews.models import Review
    from submissions.models import STATUS_ACCEPTED

    review = (
        Review.objects
        .filter(id=review_id)
        .select_related("assignment__submission__author", "assignment__reviewer")
        .first()
    )
    if not review:
        return {"status": "skipped", "reason": "review_not_found"}

    assignment = review.assignment
    submission = assignment.submission
    if submission.editorial_decision != "accept" or submission.status != STATUS_ACCEPTED:
        return {"status": "skipped", "reason": "editor_decision_not_accept"}

    author = submission.author
    reviewer = assignment.reviewer

    to_email = getattr(author, "email", None)
    if not to_email:
        return {"status": "skipped", "reason": "author_email_missing"}

    author_name = (getattr(author, "full_name", "") or "").strip() or "Author"
    reviewer_name = (
        (getattr(reviewer, "full_name", "") or "").strip()
        or (getattr(reviewer, "email", "") or "").strip()
        or "Reviewer"
    )

    reviewer_comment_parts = []
    if review.summary:
        reviewer_comment_parts.append(f"Summary: {review.summary}")
    if review.strengths:
        reviewer_comment_parts.append(f"Strengths: {review.strengths}")
    if review.weaknesses:
        reviewer_comment_parts.append(f"Weaknesses: {review.weaknesses}")
    reviewer_comment = "\n".join(reviewer_comment_parts).strip()
    editor_comment = (submission.decision_letter or "").strip()

    certificate, _ = ReviewerRecognitionCertificate.objects.get_or_create(
        review=review,
        defaults={
            "submission": submission,
            "author": author,
            "reviewer": reviewer,
            "article_title": submission.title or "Untitled article",
            "author_full_name": author_name,
            "reviewer_full_name": reviewer_name,
        },
    )

    # Keep certificate metadata synchronized with latest names/titles.
    updated = False
    if certificate.article_title != (submission.title or "Untitled article"):
        certificate.article_title = submission.title or "Untitled article"
        updated = True
    if certificate.author_full_name != author_name:
        certificate.author_full_name = author_name
        updated = True
    if certificate.reviewer_full_name != reviewer_name:
        certificate.reviewer_full_name = reviewer_name
        updated = True
    if certificate.author_id != author.id:
        certificate.author = author
        updated = True
    if certificate.reviewer_id != getattr(reviewer, "id", None):
        certificate.reviewer = reviewer
        updated = True
    if certificate.submission_id != submission.id:
        certificate.submission = submission
        updated = True
    if updated:
        certificate.save()

    certificate_page_url = build_frontend_certificate_url(certificate.verification_code)
    certificate_pdf = build_reviewer_recognition_pdf(
        submission_title=certificate.article_title,
        author_full_name=author_name,
        reviewer_full_name=reviewer_name,
        issued_at=certificate.issued_at,
        verification_url=certificate_page_url,
        reviewer_comment=reviewer_comment,
        editor_comment=editor_comment,
    )

    subject = "Reviewer Recognition Certificate"
    body = (
        f"Dear {author_name},\n\n"
        "Your submission received a positive reviewer recommendation.\n"
        f"Article: {certificate.article_title}\n"
        f"Reviewer: {reviewer_name}\n"
        f"Certificate page: {certificate_page_url}\n\n"
        "Please find the reviewer recognition certificate attached as PDF.\n\n"
        "Best regards,\n"
        "Ditech Asia Editorial Team"
    )
    filename = f"reviewer-recognition-{certificate.verification_code}.pdf"

    email_log = EmailLog.objects.create(
        to_email=to_email,
        subject=subject,
        body=body,
        status="queued",
    )

    try:
        html_message = None
        try:
            from .email_html import wrap_email_html
            html_message = wrap_email_html(subject, body)
        except Exception:
            logger.exception("Failed to render HTML email for reviewer certificate")

        backend = get_email_backend()
        provider_msg_id = backend.send(
            to_email=to_email,
            subject=subject,
            body=body,
            from_email=get_sender_header(),
            html_message=html_message,
            attachments=[
                {
                    "filename": filename,
                    "content": certificate_pdf,
                    "mimetype": "application/pdf",
                }
            ],
        )
    except Exception as exc:
        email_log.status = STATUS_FAILED
        email_log.error = str(exc)
        email_log.save(update_fields=["status", "error"])
        raise

    email_log.status = STATUS_SENT
    if provider_msg_id:
        email_log.provider_message_id = provider_msg_id
        email_log.save(update_fields=["status", "provider_message_id"])
    else:
        email_log.save(update_fields=["status"])
    return {
        "status": "sent",
        "to_email": to_email,
        "review_id": review_id,
        "submission_id": submission.id,
        "certificate_id": certificate.id,
        "certificate_code": str(certificate.verification_code),
    }


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_issue_author_journal_certificate_emails(self, issue_id: int):
    """
    Send journal publication certificate to each author inside a published issue.
    Triggered after Make Journal succeeds.
    """
    from submissions.models import JournalIssue

    issue = (
        JournalIssue.objects
        .filter(id=issue_id)
        .prefetch_related("articles__author")
        .first()
    )
    if not issue:
        return {"status": "skipped", "reason": "issue_not_found"}

    sent = 0
    skipped = 0
    failed = 0
    results = []

    submissions = issue.articles.select_related("author").order_by("issue_order", "id")
    if not submissions.exists():
        return {"status": "skipped", "reason": "issue_has_no_articles"}

    for submission in submissions:
        author = submission.author
        to_email = getattr(author, "email", None)
        if not to_email:
            skipped += 1
            results.append(
                {
                    "submission_id": submission.id,
                    "status": "skipped",
                    "reason": "author_email_missing",
                }
            )
            continue

        author_name = (getattr(author, "full_name", "") or "").strip() or "Author"
        certificate, _ = JournalPublicationCertificate.objects.get_or_create(
            issue=issue,
            submission=submission,
            author=author,
            defaults={
                "article_title": submission.title or "Untitled article",
                "author_full_name": author_name,
                "issue_title": issue.title,
                "volume": issue.volume,
                "issue_number": issue.issue_number,
                "publication_year": issue.publication_year,
                "publication_date": issue.publication_date,
            },
        )

        changed = False
        if certificate.article_title != (submission.title or "Untitled article"):
            certificate.article_title = submission.title or "Untitled article"
            changed = True
        if certificate.author_full_name != author_name:
            certificate.author_full_name = author_name
            changed = True
        if certificate.issue_title != issue.title:
            certificate.issue_title = issue.title
            changed = True
        if certificate.volume != issue.volume:
            certificate.volume = issue.volume
            changed = True
        if certificate.issue_number != issue.issue_number:
            certificate.issue_number = issue.issue_number
            changed = True
        if certificate.publication_year != issue.publication_year:
            certificate.publication_year = issue.publication_year
            changed = True
        if certificate.publication_date != issue.publication_date:
            certificate.publication_date = issue.publication_date
            changed = True
        if changed:
            certificate.save()

        # Idempotency: one certificate email per issue+submission+author.
        if certificate.email_sent_at:
            skipped += 1
            results.append(
                {
                    "submission_id": submission.id,
                    "author_email": to_email,
                    "status": "skipped",
                    "reason": "already_sent",
                    "certificate_id": certificate.id,
                }
            )
            continue

        pdf_bytes = build_journal_publication_certificate_pdf(
            author_full_name=certificate.author_full_name,
            article_title=certificate.article_title,
            issue_title=certificate.issue_title,
            volume=certificate.volume,
            issue_number=certificate.issue_number,
            publication_year=certificate.publication_year,
            publication_date=certificate.publication_date,
            author_affiliation=getattr(author, "affiliation", "") or "",
            author_country=getattr(author, "country", "") or "",
            certificate_code=str(certificate.verification_code),
        )

        publication_label = (
            issue.publication_date.strftime("%d %B %Y")
            if issue.publication_date
            else str(issue.publication_year)
        )
        author_scholar_url = (getattr(author, "google_scholar_url", "") or "").strip()

        subject = f"Journal Certificate - Volume {issue.volume}, Issue {issue.issue_number}"
        certificate_url = build_frontend_journal_certificate_url(certificate.verification_code)
        
        # Plain text fallback body for email log
        scholar_line = (
            f"Google Scholar profile: {author_scholar_url}"
            if author_scholar_url
            else "Add your Google Scholar profile: https://scholar.google.com/citations"
        )
        body = (
            f"Dear {certificate.author_full_name},\n\n"
            "Your article has been included in a published journal issue.\n\n"
            f"Journal: {getattr(settings, 'JOURNAL_NAME', 'Ditech Asia')}\n"
            f"Issue: Volume {issue.volume}, Issue {issue.issue_number}\n"
            f"Publication date: {publication_label}\n"
            f"Article: {certificate.article_title}\n\n"
            f"Certificate page: {certificate_url}\n\n"
            f"{scholar_line}\n\n"
            "Please find your Journal Certificate attached as PDF.\n\n"
            "Best regards,\n"
            "Ditech Asia Editorial Team"
        )

        filename = f"journal-certificate-{certificate.verification_code}.pdf"
        email_log = EmailLog.objects.create(
            to_email=to_email,
            subject=subject,
            body=body,
            status="queued",
        )

        try:
            from .email_html import build_journal_certificate_email_html

            # Build HTML email with explicit links
            html_message = build_journal_certificate_email_html(
                subject=subject,
                author_name=certificate.author_full_name,
                journal_name=getattr(settings, "JOURNAL_NAME", "Ditech Asia"),
                volume=issue.volume,
                issue_number=issue.issue_number,
                publication_date=publication_label,
                article_title=certificate.article_title,
                certificate_url=certificate_url,
                google_scholar_url=author_scholar_url,
            )

            backend = get_email_backend()
            provider_msg_id = backend.send(
                to_email=to_email,
                subject=subject,
                body=body,
                from_email=get_sender_header(),
                html_message=html_message,
                attachments=[
                    {
                        "filename": filename,
                        "content": pdf_bytes,
                        "mimetype": "application/pdf",
                    }
                ],
            )
            certificate.email_sent_at = timezone.now()
            certificate.save(update_fields=["email_sent_at"])
            email_log.status = STATUS_SENT
            if provider_msg_id:
                email_log.provider_message_id = provider_msg_id
                email_log.save(update_fields=["status", "provider_message_id"])
            else:
                email_log.save(update_fields=["status"])
            sent += 1
            results.append(
                {
                    "submission_id": submission.id,
                    "author_email": to_email,
                    "status": "sent",
                    "certificate_id": certificate.id,
                }
            )
        except Exception as exc:
            failed += 1
            email_log.status = STATUS_FAILED
            email_log.error = str(exc)
            email_log.save(update_fields=["status", "error"])
            results.append(
                {
                    "submission_id": submission.id,
                    "author_email": to_email,
                    "status": "failed",
                    "reason": str(exc),
                }
            )

    return {
        "status": "completed",
        "issue_id": issue_id,
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }

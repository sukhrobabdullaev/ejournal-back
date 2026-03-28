"""Celery tasks for email notifications."""
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from .certificate_utils import build_frontend_certificate_url
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


def get_email_backend():
    """Return configured email backend."""
    use_provider = getattr(settings, "EMAIL_USE_PROVIDER", False)
    if use_provider:
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
        from .email_html import wrap_email_html
        html_message = wrap_email_html(subject, body)
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
    body = f"""You have a pending review for the submission "{submission.title}".

Please submit your review by {assignment.due_date or 'the given deadline'}.

Login to the journal system to access your assignments.
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

    author_name = getattr(author, "full_name", "") or "Author"
    reviewer_name = getattr(reviewer, "full_name", "") or getattr(reviewer, "email", "") or "Reviewer"
    reviewer_comment_parts = [
        f"Summary: {review.summary}" if review.summary else "",
        f"Strengths: {review.strengths}" if review.strengths else "",
        f"Weaknesses: {review.weaknesses}" if review.weaknesses else "",
    ]
    reviewer_comment = "\n".join([part for part in reviewer_comment_parts if part]).strip()
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
    # Keep display fields in sync if user/submission names changed.
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

    subject = "Reviewer recognize your article"
    body = (
        f"Dear {author_name},\n\n"
        "Congratulations. Your manuscript has received an 'accept' recommendation from the reviewer.\n"
        f"Article: {certificate.article_title}\n"
        f"Reviewer: {reviewer_name}\n"
        f"Issued date: {certificate.issued_at:%d %B %Y}\n"
        f"Certificate page: {certificate_page_url}\n\n"
        f"Reviewer comments:\n{reviewer_comment or 'Not provided.'}\n\n"
        f"Editor comment:\n{editor_comment or 'Not provided.'}\n\n"
        "Please find the recognition certificate attached as a PDF.\n\n"
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
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=get_sender_header(),
            to=[to_email],
        )
        email.attach(filename, certificate_pdf, "application/pdf")
        email.send(fail_silently=False)
    except Exception as exc:
        email_log.status = STATUS_FAILED
        email_log.error = str(exc)
        email_log.save(update_fields=["status", "error"])
        raise

    email_log.status = STATUS_SENT
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
        subject = f"Journal Certificate - Volume {issue.volume}, Issue {issue.issue_number}"
        body = (
            f"Dear {certificate.author_full_name},\n\n"
            "Your article has been included in a published journal issue.\n\n"
            f"Journal: {getattr(settings, 'JOURNAL_NAME', 'Ditech Asia')}\n"
            f"Issue: Volume {issue.volume}, Issue {issue.issue_number}\n"
            f"Publication date: {publication_label}\n"
            f"Article: {certificate.article_title}\n\n"
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
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=get_sender_header(),
                to=[to_email],
            )
            email.attach(filename, pdf_bytes, "application/pdf")
            email.send(fail_silently=False)
            certificate.email_sent_at = timezone.now()
            certificate.save(update_fields=["email_sent_at"])
            email_log.status = STATUS_SENT
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

"""Notification trigger helpers. Call these from views/signals to queue emails."""
from django.db import transaction

from .certificate_utils import (
    build_frontend_dashboard_url,
    build_frontend_editor_dashboard_url,
    build_frontend_review_invite_url,
    build_frontend_submission_url,
)
from .tasks import send_notification_email, send_review_reminder


def _compose_email(title: str, intro: str, bullets: list[str] | None = None, cta_label: str | None = None, cta_url: str | None = None, closing: str | None = None) -> str:
    lines = [title, "", intro]
    if bullets:
        lines.append("")
        for bullet in bullets:
            lines.append(f"- {bullet}")
    if cta_label and cta_url:
        lines.extend(["", f"{cta_label}: {cta_url}"])
    if closing:
        lines.extend(["", closing])
    return "\n".join(lines)


def queue_email_verification(user_id: int, to_email: str, verification_url: str, journal_name: str | None = None):
    """Queue email verification message for new signup."""
    body = _compose_email(
        "Welcome to the journal platform",
        "Your account has been created successfully.",
        [
            "Verify your email address to activate your account.",
            "After verification, you can submit papers, review manuscripts, or open the editorial dashboard.",
        ],
        "Verify email",
        verification_url,
        "If you did not create this account, you can safely ignore this email.",
    )
    transaction.on_commit(lambda: send_notification_email.delay(
        event_type="email_verification",
        user_id=user_id,
        to_email=to_email,
        subject="Verify your email address to activate your account",
        body=body,
        payload={"verification_url": verification_url, "journal_name": journal_name},
    ))


def queue_profile_updated(user_id: int, to_email: str, roles: list[str], changed_fields: list[str], journal_name: str | None = None):
    """Queue profile update confirmation for author/editor/reviewer users."""
    role_labels = ", ".join(role.title() for role in roles) if roles else "User"
    dashboard_url = build_frontend_dashboard_url()
    pretty_changed = [field.replace("_", " ").title() for field in changed_fields]

    body = _compose_email(
        "Profile settings updated",
        f"Your academic profile was updated successfully for role(s): {role_labels}.",
        pretty_changed,
        "Open dashboard",
        dashboard_url,
        "If you did not make this change, please reset your password and contact support.",
    )

    transaction.on_commit(lambda: send_notification_email.delay(
        event_type="profile_updated",
        user_id=user_id,
        to_email=to_email,
        subject="Your academic profile has been updated",
        body=body,
        payload={
            "roles": roles,
            "changed_fields": changed_fields,
            "dashboard_url": dashboard_url,
            "journal_name": journal_name,
        },
    ))


def queue_submission_submitted(submission_id: int, author_email: str, author_id: int, journal_name: str | None = None):
    """Queue email when submission is submitted."""
    submission_url = build_frontend_submission_url(submission_id)
    dashboard_url = build_frontend_dashboard_url()
    transaction.on_commit(lambda: send_notification_email.delay(
        event_type="submission_submitted",
        user_id=author_id,
        to_email=author_email,
        subject="Submission received and queued for review",
        body=_compose_email(
            f"Submission #{submission_id} received",
            "Your manuscript has been successfully submitted and is now queued for editorial processing.",
            [
                "The editorial team will perform an initial check.",
                "You can follow the status from your dashboard.",
            ],
            "Open submission",
            submission_url,
            f"Dashboard: {dashboard_url}",
        ),
        payload={"submission_id": submission_id, "submission_url": submission_url, "dashboard_url": dashboard_url, "journal_name": journal_name},
    ))


def queue_status_changed(
    submission_id: int,
    old_status: str,
    new_status: str,
    recipient_email: str,
    recipient_id: int | None,
    idempotency_key: str,
    reason: str | None = None,
    journal_name: str | None = None,
):
    """Queue status change email (idempotent)."""
    submission_url = build_frontend_submission_url(submission_id)
    lines = [
        f"Submission #{submission_id} status update",
        "",
        f"Status changed from {old_status} to {new_status}.",
    ]
    if reason:
        lines.append("")
        lines.append("Editor note:")
        lines.append("")
        lines.append(reason)

    lines.extend(["", f"Open submission: {submission_url}"])

    body = "\n".join(lines)
    payload: dict = {
        "submission_id": submission_id,
        "old_status": old_status,
        "new_status": new_status,
        "submission_url": submission_url,
        "journal_name": journal_name,
    }
    if reason:
        payload["reason"] = reason

    transaction.on_commit(lambda: send_notification_email.delay(
        event_type="status_changed",
        user_id=recipient_id,
        to_email=recipient_email,
        subject=f"Submission status update: {new_status}",
        body=body,
        payload=payload,
        idempotency_key=idempotency_key,
    ))


def queue_reviewer_invited(
    assignment_id: int,
    to_email: str,
    submission_title: str,
    invite_token: str | None = None,
    journal_name: str | None = None,
):
    """Queue reviewer invitation email."""
    invite_url = build_frontend_review_invite_url(invite_token) if invite_token else ""
    transaction.on_commit(lambda: send_notification_email.delay(
        event_type="reviewer_invited",
        user_id=None,
        to_email=to_email,
        subject=f"Review invitation: {submission_title[:50]}",
        body=_compose_email(
            f"Review invitation: {submission_title}",
            "You have been invited to review a manuscript in the journal system.",
            [
                "Review the invitation details.",
                "Accept or decline from the linked reviewer page.",
            ],
            "Open invitation",
            invite_url or None,
            "Thank you for supporting the peer review process.",
        ),
        payload={"assignment_id": assignment_id, "invite_url": invite_url, "journal_name": journal_name},
    ))


def queue_reviewer_accepted(assignment_id: int, editor_emails: list[str], submission_title: str, journal_name: str | None = None):
    """Queue email to editors when reviewer accepts."""
    dashboard_url = build_frontend_editor_dashboard_url()
    for email in editor_emails:
        transaction.on_commit(lambda email=email: send_notification_email.delay(
            event_type="reviewer_accepted",
            user_id=None,
            to_email=email,
            subject=f"Reviewer accepted: {submission_title[:50]}",
            body=_compose_email(
                f"Reviewer accepted: {submission_title}",
                "A reviewer has accepted the invitation and can continue with the manuscript.",
                ["Open the editorial dashboard to review the assignment status."],
                "Open editorial dashboard",
                dashboard_url,
            ),
            payload={"assignment_id": assignment_id, "dashboard_url": dashboard_url, "journal_name": journal_name},
        ))


def queue_reviewer_declined(assignment_id: int, editor_emails: list[str], submission_title: str, journal_name: str | None = None):
    """Queue email to editors when reviewer declines."""
    dashboard_url = build_frontend_editor_dashboard_url()
    for email in editor_emails:
        transaction.on_commit(lambda email=email: send_notification_email.delay(
            event_type="reviewer_declined",
            user_id=None,
            to_email=email,
            subject=f"Reviewer declined: {submission_title[:50]}",
            body=_compose_email(
                f"Reviewer declined: {submission_title}",
                "A reviewer has declined the invitation for this submission.",
                ["Open the editorial dashboard to assign another reviewer if needed."],
                "Open editorial dashboard",
                dashboard_url,
            ),
            payload={"assignment_id": assignment_id, "dashboard_url": dashboard_url, "journal_name": journal_name},
        ))


def queue_review_submitted(submission_id: int, editor_emails: list[str], submission_title: str, journal_name: str | None = None):
    """Queue email when review is submitted."""
    dashboard_url = build_frontend_editor_dashboard_url()
    for email in editor_emails:
        transaction.on_commit(lambda email=email: send_notification_email.delay(
            event_type="review_submitted",
            user_id=None,
            to_email=email,
            subject=f"Review submitted: {submission_title[:50]}",
            body=_compose_email(
                f"Review submitted: {submission_title}",
                "A reviewer has submitted their feedback for this manuscript.",
                ["Open the editorial dashboard to read the submitted review."],
                "Open editorial dashboard",
                dashboard_url,
            ),
            payload={"submission_id": submission_id, "dashboard_url": dashboard_url, "journal_name": journal_name},
        ))


def queue_revision_requested(
    submission_id: int, author_email: str, author_id: int, decision_letter: str, journal_name: str | None = None
):
    """Queue email when revision is requested."""
    submission_url = build_frontend_submission_url(submission_id)
    transaction.on_commit(lambda: send_notification_email.delay(
        event_type="revision_requested",
        user_id=author_id,
        to_email=author_email,
        subject="Revision requested for your submission",
        body=_compose_email(
            f"Revision requested for submission #{submission_id}",
            "The editorial team has requested changes before the manuscript can move forward.",
            [decision_letter or "No editor note was provided."],
            "Open submission",
            submission_url,
        ),
        payload={"submission_id": submission_id, "submission_url": submission_url, "journal_name": journal_name},
    ))


def queue_submission_accepted(submission_id: int, author_email: str, author_id: int, journal_name: str | None = None):
    """Queue email when submission is accepted."""
    submission_url = build_frontend_submission_url(submission_id)
    transaction.on_commit(lambda: send_notification_email.delay(
        event_type="submission_accepted",
        user_id=author_id,
        to_email=author_email,
        subject="Your submission has been accepted",
        body=_compose_email(
            f"Congratulations, your submission #{submission_id} has been accepted",
            "Your manuscript successfully passed the editorial decision stage.",
            ["You can review the submission record from your dashboard."],
            "Open submission",
            submission_url,
        ),
        payload={"submission_id": submission_id, "submission_url": submission_url, "journal_name": journal_name},
    ))


def queue_submission_rejected(
    submission_id: int, author_email: str, author_id: int, decision_letter: str, journal_name: str | None = None
):
    """Queue email when submission is rejected."""
    submission_url = build_frontend_submission_url(submission_id)
    transaction.on_commit(lambda: send_notification_email.delay(
        event_type="submission_rejected",
        user_id=author_id,
        to_email=author_email,
        subject="Update on your submission",
        body=_compose_email(
            f"Submission #{submission_id} was not accepted",
            "The editorial team has completed the review process and decided not to proceed with publication.",
            [decision_letter or "No decision letter was provided."],
            "Open submission",
            submission_url,
        ),
        payload={"submission_id": submission_id, "reason": decision_letter, "submission_url": submission_url, "journal_name": journal_name},
    ))


def queue_submission_published(submission_id: int, author_email: str, author_id: int, journal_name: str | None = None):
    """Queue email when submission is published."""
    from django.contrib.auth import get_user_model

    scholar_setup_url = "https://scholar.google.com/citations"
    author_scholar_url = ""
    user_model = get_user_model()
    author = user_model.objects.filter(id=author_id).only("google_scholar_url").first()
    if author and getattr(author, "google_scholar_url", ""):
        author_scholar_url = author.google_scholar_url.strip()

    scholar_line = (
        f"Your Google Scholar profile: {author_scholar_url}"
        if author_scholar_url
        else f"Add your Google Scholar profile: {scholar_setup_url}"
    )

    submission_url = build_frontend_submission_url(submission_id)
    transaction.on_commit(lambda: send_notification_email.delay(
        event_type="submission_published",
        user_id=author_id,
        to_email=author_email,
        subject="Your submission has been published",
        body=_compose_email(
            f"Your submission #{submission_id} has been published",
            "The final publication step is complete and the article is now part of the journal record.",
            [
                "Use the link below to view the submission details.",
                scholar_line,
            ],
            "Open submission",
            submission_url,
        ),
        payload={
            "submission_id": submission_id,
            "submission_url": submission_url,
            "google_scholar_url": author_scholar_url,
            "google_scholar_setup_url": scholar_setup_url,
            "journal_name": journal_name,
        },
    ))


def queue_review_reminder_email(assignment_id: int):
    """Queue review reminder email (called from editorial remind action)."""
    transaction.on_commit(lambda: send_review_reminder.delay(assignment_id))


def queue_reviewer_approved(to_email: str, user_id: int, journal_name: str | None = None):
    """Queue email when admin approves reviewer role."""
    transaction.on_commit(lambda: send_notification_email.delay(
        event_type="reviewer_approved",
        user_id=user_id,
        to_email=to_email,
        subject="Your reviewer role has been approved",
        body=_compose_email(
            "Your reviewer role has been approved",
            "You can now accept invitations and submit reviews.",
            ["Open the dashboard to start reviewing assigned manuscripts."],
            "Open dashboard",
            build_frontend_dashboard_url(),
        ),
        payload={"user_id": user_id, "journal_name": journal_name},
    ))


def queue_editor_approved(to_email: str, user_id: int, journal_name: str | None = None):
    """Queue email when admin approves editor role."""
    transaction.on_commit(lambda: send_notification_email.delay(
        event_type="editor_approved",
        user_id=user_id,
        to_email=to_email,
        subject="Your editor role has been approved",
        body=_compose_email(
            "Your editor role has been approved",
            "You now have access to the editorial workspace.",
            ["Open the editorial dashboard to screen submissions, manage reviews, and publish issues."],
            "Open editorial dashboard",
            build_frontend_editor_dashboard_url(),
        ),
        payload={"user_id": user_id, "journal_name": journal_name},
    ))

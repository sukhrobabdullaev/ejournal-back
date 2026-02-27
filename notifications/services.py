"""Notification trigger helpers. Call these from views/signals to queue emails."""
from .tasks import send_notification_email, send_review_reminder


def queue_submission_submitted(submission_id: int, author_email: str, author_id: int):
    """Queue email when submission is submitted."""
    send_notification_email.delay(
        event_type="submission_submitted",
        user_id=author_id,
        to_email=author_email,
        subject="Your submission has been received",
        body=f"Your submission (ID: {submission_id}) has been received and is under review.",
        payload={"submission_id": submission_id},
    )


def queue_status_changed(
    submission_id: int,
    old_status: str,
    new_status: str,
    recipient_email: str,
    recipient_id: int | None,
    idempotency_key: str,
):
    """Queue status change email (idempotent)."""
    send_notification_email.delay(
        event_type="status_changed",
        user_id=recipient_id,
        to_email=recipient_email,
        subject=f"Submission status update: {new_status}",
        body=f"Submission {submission_id} status changed from {old_status} to {new_status}.",
        payload={"submission_id": submission_id, "old_status": old_status, "new_status": new_status},
        idempotency_key=idempotency_key,
    )


def queue_reviewer_invited(assignment_id: int, to_email: str, submission_title: str):
    """Queue reviewer invitation email."""
    send_notification_email.delay(
        event_type="reviewer_invited",
        user_id=None,
        to_email=to_email,
        subject=f"Review invitation: {submission_title[:50]}",
        body=f"You have been invited to review the submission: {submission_title}. Please log in to accept or decline.",
        payload={"assignment_id": assignment_id},
    )


def queue_reviewer_accepted(assignment_id: int, editor_emails: list[str], submission_title: str):
    """Queue email to editors when reviewer accepts."""
    for email in editor_emails:
        send_notification_email.delay(
            event_type="reviewer_accepted",
            user_id=None,
            to_email=email,
            subject=f"Reviewer accepted: {submission_title[:50]}",
            body=f"A reviewer has accepted the invitation for submission: {submission_title}.",
            payload={"assignment_id": assignment_id},
        )


def queue_reviewer_declined(assignment_id: int, editor_emails: list[str], submission_title: str):
    """Queue email to editors when reviewer declines."""
    for email in editor_emails:
        send_notification_email.delay(
            event_type="reviewer_declined",
            user_id=None,
            to_email=email,
            subject=f"Reviewer declined: {submission_title[:50]}",
            body=f"A reviewer has declined the invitation for submission: {submission_title}.",
            payload={"assignment_id": assignment_id},
        )


def queue_review_submitted(submission_id: int, editor_emails: list[str], submission_title: str):
    """Queue email when review is submitted."""
    for email in editor_emails:
        send_notification_email.delay(
            event_type="review_submitted",
            user_id=None,
            to_email=email,
            subject=f"Review submitted: {submission_title[:50]}",
            body=f"A review has been submitted for: {submission_title}.",
            payload={"submission_id": submission_id},
        )


def queue_revision_requested(
    submission_id: int, author_email: str, author_id: int, decision_letter: str
):
    """Queue email when revision is requested."""
    send_notification_email.delay(
        event_type="revision_requested",
        user_id=author_id,
        to_email=author_email,
        subject="Revision requested for your submission",
        body=f"Revision has been requested for your submission (ID: {submission_id}).\n\n{decision_letter}",
        payload={"submission_id": submission_id},
    )


def queue_submission_accepted(submission_id: int, author_email: str, author_id: int):
    """Queue email when submission is accepted."""
    send_notification_email.delay(
        event_type="submission_accepted",
        user_id=author_id,
        to_email=author_email,
        subject="Your submission has been accepted",
        body=f"Congratulations! Your submission (ID: {submission_id}) has been accepted.",
        payload={"submission_id": submission_id},
    )


def queue_submission_rejected(
    submission_id: int, author_email: str, author_id: int, decision_letter: str
):
    """Queue email when submission is rejected."""
    send_notification_email.delay(
        event_type="submission_rejected",
        user_id=author_id,
        to_email=author_email,
        subject="Update on your submission",
        body=f"Your submission (ID: {submission_id}) was not accepted.\n\n{decision_letter}",
        payload={"submission_id": submission_id},
    )


def queue_submission_published(submission_id: int, author_email: str, author_id: int):
    """Queue email when submission is published."""
    send_notification_email.delay(
        event_type="submission_published",
        user_id=author_id,
        to_email=author_email,
        subject="Your submission has been published",
        body=f"Your submission (ID: {submission_id}) has been published.",
        payload={"submission_id": submission_id},
    )


def queue_review_reminder_email(assignment_id: int):
    """Queue review reminder email (called from editorial remind action)."""
    send_review_reminder.delay(assignment_id)

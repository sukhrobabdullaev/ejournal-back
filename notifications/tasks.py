"""Celery tasks for email notifications."""
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import EmailLog, Notification, STATUS_FAILED, STATUS_SENT


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
        backend = get_email_backend()
        provider_msg_id = backend.send(to_email, subject, body)
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

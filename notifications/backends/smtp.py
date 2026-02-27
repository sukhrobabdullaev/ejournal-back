"""SMTP email backend using Django's email system."""
from django.core.mail import send_mail
from django.conf import settings

from .base import EmailBackend


class SMTPBackend(EmailBackend):
    """Send email via Django SMTP configuration."""

    def send(self, to_email: str, subject: str, body: str, **kwargs) -> str | None:
        from_email = kwargs.get("from_email") or getattr(
            settings, "DEFAULT_FROM_EMAIL", "noreply@ejournal.local"
        )
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[to_email],
            fail_silently=False,
            html_message=kwargs.get("html_message"),
        )
        return None

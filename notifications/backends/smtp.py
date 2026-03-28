"""SMTP email backend using Django's email system."""
from django.core.mail import send_mail

from .base import EmailBackend
from ..sender import get_sender_header


class SMTPBackend(EmailBackend):
    """Send email via Django SMTP configuration."""

    def send(self, to_email: str, subject: str, body: str, **kwargs) -> str | None:
        from_email = kwargs.get("from_email") or get_sender_header()
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[to_email],
            fail_silently=False,
            html_message=kwargs.get("html_message"),
        )
        return None

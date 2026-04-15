"""SMTP email backend using Django's email system."""
from django.core.mail import EmailMultiAlternatives

from .base import EmailBackend
from ..sender import get_sender_header


class SMTPBackend(EmailBackend):
    """Send email via Django SMTP configuration."""

    def send(self, to_email: str, subject: str, body: str, **kwargs) -> str | None:
        from_email = kwargs.get("from_email") or get_sender_header()
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[to_email],
        )
        html_message = kwargs.get("html_message")
        if html_message:
            message.attach_alternative(html_message, "text/html")

        # attachments format: [{"filename": str, "content": bytes, "mimetype": str}]
        for item in kwargs.get("attachments", []) or []:
            filename = item.get("filename")
            content = item.get("content")
            mimetype = item.get("mimetype") or "application/octet-stream"
            if filename and content is not None:
                message.attach(filename, content, mimetype)

        message.send(fail_silently=False)
        return None

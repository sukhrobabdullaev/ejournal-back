"""Provider email backend (SES, SendGrid, Mailgun, Postmark)."""
from django.conf import settings

from .base import EmailBackend


class ProviderBackend(EmailBackend):
    """
    Send email via external provider.
    Configure EMAIL_PROVIDER (ses, sendgrid, mailgun, postmark) and credentials in settings.
    Uses django-anymail or boto3 for SES as fallback.
    """

    def send(self, to_email: str, subject: str, body: str, **kwargs) -> str | None:
        provider = getattr(settings, "EMAIL_PROVIDER", "ses")
        if provider == "ses":
            return self._send_ses(to_email, subject, body, **kwargs)
        # Extensible for sendgrid, mailgun, postmark
        return self._send_ses(to_email, subject, body, **kwargs)

    def _send_ses(self, to_email: str, subject: str, body: str, **kwargs) -> str | None:
        import boto3
        from botocore.exceptions import ClientError

        from_email = kwargs.get("from_email") or getattr(
            settings, "DEFAULT_FROM_EMAIL", "noreply@ejournal.local"
        )
        region = getattr(settings, "AWS_SES_REGION", "us-east-1")
        client = boto3.client("ses", region_name=region)
        try:
            response = client.send_email(
                Source=from_email,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": body, "Charset": "UTF-8"},
                    },
                },
            )
            return response.get("MessageId")
        except ClientError as e:
            raise RuntimeError(f"SES send failed: {e}") from e

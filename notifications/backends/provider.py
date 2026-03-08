"""Provider email backend (SES, SendGrid, Mailgun, Postmark, Brevo)."""
import requests
from django.conf import settings

from .base import EmailBackend


class ProviderBackend(EmailBackend):
    """
    Send email via external provider.
    Configure EMAIL_PROVIDER (ses, sendgrid, mailgun, postmark, brevo) and credentials in settings.
    Uses django-anymail or boto3 for SES as fallback.
    """

    def send(self, to_email: str, subject: str, body: str, **kwargs) -> str | None:
        provider = getattr(settings, "EMAIL_PROVIDER", "ses")
        if provider == "ses":
            return self._send_ses(to_email, subject, body, **kwargs)
        elif provider == "brevo":
            return self._send_brevo(to_email, subject, body, **kwargs)
        # Extensible for sendgrid, mailgun, postmark
        return self._send_ses(to_email, subject, body, **kwargs)

    def _send_brevo(self, to_email: str, subject: str, body: str, **kwargs) -> str | None:
        """Send email via Brevo (Sendinblue) API."""
        api_key = getattr(settings, "BREVO_API_KEY", None)
        if not api_key:
            raise RuntimeError("BREVO_API_KEY not configured")
        
        from_email = kwargs.get("from_email") or getattr(
            settings, "DEFAULT_FROM_EMAIL", "noreply@ejournal.local"
        )
        from_name = getattr(settings, "DEFAULT_FROM_NAME", "E-Journal")
        
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        }
        
        payload = {
            "sender": {"name": from_name, "email": from_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "textContent": body,
        }
        
        html_message = kwargs.get("html_message")
        if html_message:
            payload["htmlContent"] = html_message
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            return result.get("messageId")
        except requests.RequestException as e:
            raise RuntimeError(f"Brevo API send failed: {e}") from e

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

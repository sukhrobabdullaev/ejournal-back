"""Helpers for normalized sender identity across all email channels."""
from email.utils import formataddr

from django.conf import settings


def get_sender_name() -> str:
    """Return display name for outgoing emails."""
    return (
        getattr(settings, "DEFAULT_FROM_NAME", None)
        or getattr(settings, "JOURNAL_NAME", None)
        or "Ditech Asia"
    )


def get_sender_email() -> str:
    """Return sender email for outgoing emails."""
    return getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@ejournal.local")


def get_sender_header() -> str:
    """Return RFC-compliant `From` header with display name and email."""
    return formataddr((get_sender_name(), get_sender_email()))

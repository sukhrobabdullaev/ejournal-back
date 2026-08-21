"""Helpers for normalized sender identity across all email channels."""
from email.utils import formataddr

from django.conf import settings


def get_sender_name(journal=None) -> str:
    """Return display name for outgoing emails, journal-aware."""
    if journal is not None:
        return journal.effective_from_name
    return (
        getattr(settings, "DEFAULT_FROM_NAME", None)
        or getattr(settings, "JOURNAL_NAME", None)
        or "Ditech Asia"
    )


def get_sender_email() -> str:
    """Return sender email for outgoing emails."""
    return getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@ejournal.local")


def get_sender_header(journal=None) -> str:
    """Return RFC-compliant `From` header with display name and email."""
    return formataddr((get_sender_name(journal), get_sender_email()))

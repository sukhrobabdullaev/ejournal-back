"""Journal membership query helpers."""
from .models import (
    MEMBERSHIP_STATUS_APPROVED,
    JournalMembership,
)


def has_role(user, journal, role) -> bool:
    """Check if user has a given role in a given journal (regardless of status)."""
    if user is None or journal is None:
        return False
    return JournalMembership.objects.filter(user=user, journal=journal, role=role).exists()


def is_approved_reviewer(user, journal) -> bool:
    """Reviewer role + approved status, scoped to one journal."""
    if user is None or journal is None:
        return False
    return JournalMembership.objects.filter(
        user=user, journal=journal, role="reviewer", status=MEMBERSHIP_STATUS_APPROVED
    ).exists()


def is_approved_editor(user, journal) -> bool:
    """Editor role + approved status, scoped to one journal."""
    if user is None or journal is None:
        return False
    return JournalMembership.objects.filter(
        user=user, journal=journal, role="editor", status=MEMBERSHIP_STATUS_APPROVED
    ).exists()


def is_author(user, journal) -> bool:
    """Author role, scoped to one journal (no approval gate)."""
    if user is None or journal is None:
        return False
    return JournalMembership.objects.filter(user=user, journal=journal, role="author").exists()

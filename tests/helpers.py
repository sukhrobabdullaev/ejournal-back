"""Shared test helpers for creating journals and journal memberships."""
from journals.models import MEMBERSHIP_STATUS_APPROVED, Journal, JournalMembership

_counter = [0]


def make_journal(slug=None, **kwargs):
    if slug is None:
        _counter[0] += 1
        slug = f"test-journal-{_counter[0]}"
    defaults = dict(name="Test Journal", doi_prefix="10.9999", from_name="Test Journal")
    defaults.update(kwargs)
    return Journal.objects.create(slug=slug, **defaults)


def make_membership(user, journal, role, status=MEMBERSHIP_STATUS_APPROVED):
    return JournalMembership.objects.create(user=user, journal=journal, role=role, status=status)

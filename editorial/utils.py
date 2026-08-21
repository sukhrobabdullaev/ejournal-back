"""Editorial utilities."""
from journals.models import MEMBERSHIP_STATUS_APPROVED, JournalMembership


def get_editor_emails(journal):
    """Return list of approved editor emails for a journal, for notifications."""
    return list(
        JournalMembership.objects.filter(
            journal=journal, role="editor", status=MEMBERSHIP_STATUS_APPROVED
        ).values_list("user__email", flat=True)
    )

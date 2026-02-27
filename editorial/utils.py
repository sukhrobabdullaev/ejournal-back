"""Editorial utilities."""
from accounts.models import ROLE_EDITOR, APPROVAL_APPROVED, User


def get_editor_emails():
    """Return list of approved editor emails for notifications."""
    return [
        u.email
        for u in User.objects.filter(editor_status=APPROVAL_APPROVED)
        if ROLE_EDITOR in (u.roles or [])
    ]

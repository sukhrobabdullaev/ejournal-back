"""Convert each user's flat roles/reviewer_status/editor_status into
per-journal JournalMembership rows against the default 'Ditech Asia' journal.
"""
from django.db import migrations
from django.utils import timezone

DEFAULT_JOURNAL_SLUG = "ditech-asia"
VALID_ROLES = ("author", "reviewer", "editor")


def backfill_memberships(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Journal = apps.get_model("journals", "Journal")
    JournalMembership = apps.get_model("journals", "JournalMembership")

    journal = Journal.objects.filter(slug=DEFAULT_JOURNAL_SLUG).first()
    if journal is None:
        return

    now = timezone.now()

    for user in User.objects.all():
        roles = user.roles or []
        for role in roles:
            if role not in VALID_ROLES:
                continue
            status = "approved"
            approved_at = None
            if role == "reviewer":
                status = user.reviewer_status or "pending"
                approved_at = now if status == "approved" else None
            elif role == "editor":
                status = user.editor_status or "pending"
                approved_at = now if status == "approved" else None
            else:
                approved_at = now  # author has no approval gate
            JournalMembership.objects.get_or_create(
                user=user,
                journal=journal,
                role=role,
                defaults=dict(
                    status=status,
                    approved_at=approved_at,
                    why_to_be=user.why_to_be or "",
                ),
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_google_scholar_url"),
        ("journals", "0001_initial"),
        ("submissions", "0008_backfill_journal"),
    ]

    operations = [
        migrations.RunPython(backfill_memberships, noop_reverse),
    ]

"""Backfill existing editorial board members onto the default journal."""
from django.db import migrations

DEFAULT_JOURNAL_SLUG = "ditech-asia"
DEFAULT_JOURNAL_NAME = "Ditech Asia"
DEFAULT_DOI_PREFIX = "10.5555"


def backfill(apps, schema_editor):
    Journal = apps.get_model("journals", "Journal")
    EditorialBoardMember = apps.get_model("editorial_board", "EditorialBoardMember")

    journal, _ = Journal.objects.get_or_create(
        slug=DEFAULT_JOURNAL_SLUG,
        defaults=dict(
            name=DEFAULT_JOURNAL_NAME,
            tagline="",
            doi_prefix=DEFAULT_DOI_PREFIX,
            contact_email="",
            from_name=DEFAULT_JOURNAL_NAME,
            is_active=True,
        ),
    )
    EditorialBoardMember.objects.filter(journal__isnull=True).update(journal=journal)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("editorial_board", "0002_editorialboardmember_journal"),
        ("submissions", "0008_backfill_journal"),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]

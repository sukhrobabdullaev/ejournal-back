"""Backfill a default 'Ditech Asia' journal and point existing rows at it."""
from django.db import migrations

DEFAULT_JOURNAL_SLUG = "ditech-asia"
DEFAULT_JOURNAL_NAME = "Ditech Asia"
DEFAULT_DOI_PREFIX = "10.5555"


def backfill(apps, schema_editor):
    Journal = apps.get_model("journals", "Journal")
    TopicArea = apps.get_model("submissions", "TopicArea")
    JournalIssue = apps.get_model("submissions", "JournalIssue")
    Submission = apps.get_model("submissions", "Submission")

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
    TopicArea.objects.filter(journal__isnull=True).update(journal=journal)
    JournalIssue.objects.filter(journal__isnull=True).update(journal=journal)
    Submission.objects.filter(journal__isnull=True).update(journal=journal)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0007_alter_journalissue_unique_together_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]

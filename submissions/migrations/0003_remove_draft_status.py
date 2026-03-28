from django.db import migrations, models


def migrate_draft_to_submitted(apps, schema_editor):
    Submission = apps.get_model("submissions", "Submission")
    Submission.objects.filter(status="draft").update(status="submitted")


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0002_submission_editorial_fields"),
    ]

    operations = [
        migrations.RunPython(migrate_draft_to_submitted, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="submission",
            name="status",
            field=models.CharField(
                choices=[
                    ("submitted", "Submitted"),
                    ("screening", "Screening"),
                    ("desk_rejected", "Desk Rejected"),
                    ("under_review", "Under Review"),
                    ("revision_required", "Revision Required"),
                    ("resubmitted", "Resubmitted"),
                    ("decision_pending", "Decision Pending"),
                    ("accepted", "Accepted"),
                    ("rejected", "Rejected"),
                    ("published", "Published"),
                    ("withdrawn", "Withdrawn"),
                ],
                default="submitted",
                max_length=30,
            ),
        ),
    ]

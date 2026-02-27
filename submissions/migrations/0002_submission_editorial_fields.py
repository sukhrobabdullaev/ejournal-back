"""Add editorial fields to Submission."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="desk_reject_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="editorial_decision",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="submission",
            name="decision_letter",
            field=models.TextField(blank=True),
        ),
    ]

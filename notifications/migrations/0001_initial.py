"""Initial migration for notifications app."""
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("submission_submitted", "Submission Submitted"), ("status_changed", "Status Changed"), ("reviewer_invited", "Reviewer Invited"), ("reviewer_accepted", "Reviewer Accepted"), ("reviewer_declined", "Reviewer Declined"), ("review_submitted", "Review Submitted"), ("revision_requested", "Revision Requested"), ("submission_accepted", "Submission Accepted"), ("submission_rejected", "Submission Rejected"), ("submission_published", "Submission Published"), ("review_reminder", "Review Reminder")], max_length=50)),
                ("payload", models.JSONField(default=dict)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("sent", "Sent"), ("failed", "Failed")], default="queued", max_length=20)),
                ("idempotency_key", models.CharField(blank=True, db_index=True, max_length=128)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "notifications_notification",
            },
        ),
        migrations.CreateModel(
            name="EmailLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("to_email", models.EmailField(max_length=254)),
                ("subject", models.CharField(max_length=500)),
                ("body", models.TextField(blank=True)),
                ("provider_message_id", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(default="queued", max_length=20)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "notifications_email_log",
            },
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["event_type", "idempotency_key"], name="notif_event_idemp_idx"),
        ),
    ]

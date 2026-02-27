"""Initial migration for reviews app."""
import secrets

from django.conf import settings
from django.db import migrations, models


def gen_token():
    return secrets.token_urlsafe(32)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("submissions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReviewAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("invited_email", models.EmailField(blank=True, max_length=254)),
                ("token", models.CharField(default=gen_token, max_length=64, unique=True)),
                ("status", models.CharField(choices=[("invited", "Invited"), ("accepted", "Accepted"), ("declined", "Declined"), ("review_submitted", "Review Submitted"), ("expired", "Expired")], default="invited", max_length=20)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("invited_at", models.DateTimeField(auto_now_add=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("reviewer", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="review_assignments", to=settings.AUTH_USER_MODEL)),
                ("submission", models.ForeignKey(on_delete=models.CASCADE, related_name="review_assignments", to="submissions.submission")),
                ("submission_version", models.ForeignKey(on_delete=models.CASCADE, related_name="review_assignments", to="submissions.submissionversion")),
            ],
            options={
                "db_table": "reviews_assignment",
            },
        ),
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("summary", models.TextField()),
                ("strengths", models.TextField(blank=True)),
                ("weaknesses", models.TextField(blank=True)),
                ("confidential_to_editor", models.TextField(blank=True)),
                ("recommendation", models.CharField(choices=[("accept", "Accept"), ("minor_revision", "Minor Revision"), ("major_revision", "Major Revision"), ("reject", "Reject")], max_length=20)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("assignment", models.OneToOneField(on_delete=models.CASCADE, related_name="review", to="reviews.reviewassignment")),
            ],
            options={
                "db_table": "reviews_review",
            },
        ),
    ]

"""Initial migration for submissions app."""
from django.conf import settings
from django.db import migrations, models
import submissions.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TopicArea",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
            ],
            options={
                "db_table": "submissions_topic_area",
            },
        ),
        migrations.CreateModel(
            name="Submission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("draft", "Draft"), ("submitted", "Submitted"), ("screening", "Screening"), ("desk_rejected", "Desk Rejected"), ("under_review", "Under Review"), ("revision_required", "Revision Required"), ("resubmitted", "Resubmitted"), ("decision_pending", "Decision Pending"), ("accepted", "Accepted"), ("rejected", "Rejected"), ("published", "Published"), ("withdrawn", "Withdrawn")], default="draft", max_length=30)),
                ("originality_confirmation", models.BooleanField(default=False)),
                ("originality_confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("plagiarism_agreement", models.BooleanField(default=False)),
                ("plagiarism_agreed_at", models.DateTimeField(blank=True, null=True)),
                ("ethics_compliance", models.BooleanField(default=False)),
                ("ethics_confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("copyright_agreement", models.BooleanField(default=False)),
                ("copyright_agreed_at", models.DateTimeField(blank=True, null=True)),
                ("title", models.CharField(blank=True, max_length=500)),
                ("abstract", models.TextField(blank=True)),
                ("keywords", models.JSONField(default=list)),
                ("manuscript_pdf", models.FileField(blank=True, null=True, upload_to=submissions.models.manuscript_upload_path)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("author", models.ForeignKey(on_delete=models.CASCADE, related_name="submissions", to=settings.AUTH_USER_MODEL)),
                ("topic_area", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="submissions", to="submissions.topicarea")),
            ],
            options={
                "db_table": "submissions_submission",
            },
        ),
        migrations.CreateModel(
            name="SubmissionSupplementaryFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=submissions.models.supplementary_upload_path)),
                ("name", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("submission", models.ForeignKey(on_delete=models.CASCADE, related_name="supplementary_files", to="submissions.submission")),
            ],
            options={
                "db_table": "submissions_supplementary_file",
            },
        ),
        migrations.CreateModel(
            name="SubmissionVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version_number", models.PositiveIntegerField()),
                ("manuscript_pdf", models.FileField(upload_to="submissions/versions/manuscripts/")),
                ("supplementary_files_snapshot", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("submission", models.ForeignKey(on_delete=models.CASCADE, related_name="versions", to="submissions.submission")),
            ],
            options={
                "db_table": "submissions_version",
                "ordering": ["submission", "version_number"],
                "unique_together": {("submission", "version_number")},
            },
        ),
    ]

"""Submission models."""
from django.conf import settings
from django.db import models


class TopicArea(models.Model):
    """Topic/field for manuscript categorization (e.g., AI, SWE)."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = "submissions_topic_area"

    def __str__(self):
        return self.name


# Submission status constants
STATUS_DRAFT = "draft"
STATUS_SUBMITTED = "submitted"
STATUS_SCREENING = "screening"
STATUS_DESK_REJECTED = "desk_rejected"
STATUS_UNDER_REVIEW = "under_review"
STATUS_REVISION_REQUIRED = "revision_required"
STATUS_RESUBMITTED = "resubmitted"
STATUS_DECISION_PENDING = "decision_pending"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"
STATUS_PUBLISHED = "published"
STATUS_WITHDRAWN = "withdrawn"

STATUS_CHOICES = [
    (STATUS_DRAFT, "Draft"),
    (STATUS_SUBMITTED, "Submitted"),
    (STATUS_SCREENING, "Screening"),
    (STATUS_DESK_REJECTED, "Desk Rejected"),
    (STATUS_UNDER_REVIEW, "Under Review"),
    (STATUS_REVISION_REQUIRED, "Revision Required"),
    (STATUS_RESUBMITTED, "Resubmitted"),
    (STATUS_DECISION_PENDING, "Decision Pending"),
    (STATUS_ACCEPTED, "Accepted"),
    (STATUS_REJECTED, "Rejected"),
    (STATUS_PUBLISHED, "Published"),
    (STATUS_WITHDRAWN, "Withdrawn"),
]

FINAL_STATUSES = [STATUS_DESK_REJECTED, STATUS_REJECTED, STATUS_PUBLISHED, STATUS_WITHDRAWN]


def manuscript_upload_path(instance, filename):
    """Upload path for manuscript PDF."""
    pk = instance.pk or "temp"
    return f"submissions/{pk}/manuscripts/{filename}"


def supplementary_upload_path(instance, filename):
    """Upload path for supplementary files."""
    return f"submissions/{instance.submission_id}/supplementary/{filename}"


class Submission(models.Model):
    """Manuscript submission with step-by-step data."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # Step 1: Agreements
    originality_confirmation = models.BooleanField(default=False)
    originality_confirmed_at = models.DateTimeField(null=True, blank=True)
    plagiarism_agreement = models.BooleanField(default=False)
    plagiarism_agreed_at = models.DateTimeField(null=True, blank=True)
    ethics_compliance = models.BooleanField(default=False)
    ethics_confirmed_at = models.DateTimeField(null=True, blank=True)
    copyright_agreement = models.BooleanField(default=False)
    copyright_agreed_at = models.DateTimeField(null=True, blank=True)

    # Step 2: Metadata
    title = models.CharField(max_length=500, blank=True)
    abstract = models.TextField(blank=True)
    keywords = models.JSONField(default=list)  # 3-10 strings
    topic_area = models.ForeignKey(
        TopicArea,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions",
    )

    # Step 3: Files (manuscript required before submit; supplementary optional)
    manuscript_pdf = models.FileField(upload_to=manuscript_upload_path, blank=True, null=True)

    # Editorial
    desk_reject_reason = models.TextField(blank=True)
    editorial_decision = models.CharField(max_length=30, blank=True)  # accept, reject, revision_required
    decision_letter = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "submissions_submission"

    def __str__(self):
        return f"{self.title or '(Untitled)'} by {self.author.email}"


class SubmissionSupplementaryFile(models.Model):
    """Supplementary file attached to a submission."""

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="supplementary_files",
    )
    file = models.FileField(upload_to=supplementary_upload_path)
    name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "submissions_supplementary_file"


class SubmissionVersion(models.Model):
    """Version snapshot for each resubmission (links to manuscript + supplementary snapshot)."""

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    manuscript_pdf = models.FileField(upload_to="submissions/versions/manuscripts/")
    supplementary_files_snapshot = models.JSONField(default=list)  # [{"name": "...", "url": "..."}]
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "submissions_version"
        unique_together = [("submission", "version_number")]
        ordering = ["submission", "version_number"]

"""Notification models."""
import uuid

from django.conf import settings
from django.db import models


# Event types for idempotency / routing
EVENT_SUBMISSION_SUBMITTED = "submission_submitted"
EVENT_STATUS_CHANGED = "status_changed"
EVENT_REVIEWER_INVITED = "reviewer_invited"
EVENT_REVIEWER_ACCEPTED = "reviewer_accepted"
EVENT_REVIEWER_DECLINED = "reviewer_declined"
EVENT_REVIEW_SUBMITTED = "review_submitted"
EVENT_REVISION_REQUESTED = "revision_requested"
EVENT_SUBMISSION_ACCEPTED = "submission_accepted"
EVENT_SUBMISSION_REJECTED = "submission_rejected"
EVENT_SUBMISSION_PUBLISHED = "submission_published"
EVENT_REVIEW_REMINDER = "review_reminder"
EVENT_EMAIL_VERIFICATION = "email_verification"
EVENT_PROFILE_UPDATED = "profile_updated"

EVENT_CHOICES = [
    (EVENT_SUBMISSION_SUBMITTED, "Submission Submitted"),
    (EVENT_STATUS_CHANGED, "Status Changed"),
    (EVENT_REVIEWER_INVITED, "Reviewer Invited"),
    (EVENT_REVIEWER_ACCEPTED, "Reviewer Accepted"),
    (EVENT_REVIEWER_DECLINED, "Reviewer Declined"),
    (EVENT_REVIEW_SUBMITTED, "Review Submitted"),
    (EVENT_REVISION_REQUESTED, "Revision Requested"),
    (EVENT_SUBMISSION_ACCEPTED, "Submission Accepted"),
    (EVENT_SUBMISSION_REJECTED, "Submission Rejected"),
    (EVENT_SUBMISSION_PUBLISHED, "Submission Published"),
    (EVENT_REVIEW_REMINDER, "Review Reminder"),
    (EVENT_EMAIL_VERIFICATION, "Email Verification"),
    (EVENT_PROFILE_UPDATED, "Profile Updated"),
]

STATUS_QUEUED = "queued"
STATUS_SENT = "sent"
STATUS_FAILED = "failed"

NOTIFICATION_STATUS_CHOICES = [
    (STATUS_QUEUED, "Queued"),
    (STATUS_SENT, "Sent"),
    (STATUS_FAILED, "Failed"),
]


class Notification(models.Model):
    """Notification event record (for idempotency and audit)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    payload = models.JSONField(default=dict)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=NOTIFICATION_STATUS_CHOICES,
        default=STATUS_QUEUED,
    )
    idempotency_key = models.CharField(max_length=128, blank=True, db_index=True)

    class Meta:
        db_table = "notifications_notification"
        indexes = [
            models.Index(fields=["event_type", "idempotency_key"]),
        ]


class EmailLog(models.Model):
    """Log of sent email for audit and debugging."""

    to_email = models.EmailField()
    subject = models.CharField(max_length=500)
    body = models.TextField(blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default=STATUS_QUEUED)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_email_log"


class ReviewerRecognitionCertificate(models.Model):
    """Recognition certificate issued to author for accepted reviewer recommendation."""

    review = models.OneToOneField(
        "reviews.Review",
        on_delete=models.CASCADE,
        related_name="recognition_certificate",
    )
    submission = models.ForeignKey(
        "submissions.Submission",
        on_delete=models.CASCADE,
        related_name="recognition_certificates",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="author_recognition_certificates",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewer_recognition_certificates",
    )
    article_title = models.CharField(max_length=500)
    author_full_name = models.CharField(max_length=255)
    reviewer_full_name = models.CharField(max_length=255)
    verification_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_reviewer_recognition_certificate"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"Certificate #{self.id} | submission={self.submission_id}"


class JournalPublicationCertificate(models.Model):
    """Certificate issued to an author when a journal issue is made/published."""

    issue = models.ForeignKey(
        "submissions.JournalIssue",
        on_delete=models.CASCADE,
        related_name="author_journal_certificates",
    )
    submission = models.ForeignKey(
        "submissions.Submission",
        on_delete=models.CASCADE,
        related_name="journal_publication_certificates",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="journal_publication_certificates",
    )
    article_title = models.CharField(max_length=500)
    author_full_name = models.CharField(max_length=255)
    issue_title = models.CharField(max_length=255)
    volume = models.PositiveIntegerField()
    issue_number = models.PositiveIntegerField()
    publication_year = models.PositiveIntegerField()
    publication_date = models.DateField(null=True, blank=True)
    verification_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_journal_publication_certificate"
        ordering = ["-issued_at"]
        unique_together = [("issue", "submission", "author")]

    def __str__(self):
        return (
            f"JournalCertificate #{self.id} | issue={self.issue_id} | "
            f"submission={self.submission_id}"
        )

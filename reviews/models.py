"""Review models."""
import secrets

from django.conf import settings
from django.db import models

from submissions.models import Submission, SubmissionVersion


STATUS_INVITED = "invited"
STATUS_ACCEPTED = "accepted"
STATUS_DECLINED = "declined"
STATUS_REVIEW_SUBMITTED = "review_submitted"
STATUS_EXPIRED = "expired"

ASSIGNMENT_STATUS_CHOICES = [
    (STATUS_INVITED, "Invited"),
    (STATUS_ACCEPTED, "Accepted"),
    (STATUS_DECLINED, "Declined"),
    (STATUS_REVIEW_SUBMITTED, "Review Submitted"),
    (STATUS_EXPIRED, "Expired"),
]

RECOMMENDATION_ACCEPT = "accept"
RECOMMENDATION_MINOR_REVISION = "minor_revision"
RECOMMENDATION_MAJOR_REVISION = "major_revision"
RECOMMENDATION_REJECT = "reject"

RECOMMENDATION_CHOICES = [
    (RECOMMENDATION_ACCEPT, "Accept"),
    (RECOMMENDATION_MINOR_REVISION, "Minor Revision"),
    (RECOMMENDATION_MAJOR_REVISION, "Major Revision"),
    (RECOMMENDATION_REJECT, "Reject"),
]


def generate_invite_token():
    """Generate a secure token for email invite accept links."""
    return secrets.token_urlsafe(32)


class ReviewAssignment(models.Model):
    """Assignment of a reviewer to a submission (or invite by email)."""

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="review_assignments",
    )
    submission_version = models.ForeignKey(
        SubmissionVersion,
        on_delete=models.CASCADE,
        related_name="review_assignments",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_assignments",
    )
    invited_email = models.EmailField(blank=True)
    token = models.CharField(max_length=64, unique=True, default=generate_invite_token)

    status = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_STATUS_CHOICES,
        default=STATUS_INVITED,
    )
    due_date = models.DateField(null=True, blank=True)
    invited_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "reviews_assignment"

    def __str__(self):
        reviewer_str = self.reviewer.email if self.reviewer else self.invited_email
        return f"{self.submission.title} <- {reviewer_str} ({self.status})"


class Review(models.Model):
    """Structured peer review for an assignment."""

    assignment = models.OneToOneField(
        ReviewAssignment,
        on_delete=models.CASCADE,
        related_name="review",
    )
    summary = models.TextField()
    strengths = models.TextField(blank=True)
    weaknesses = models.TextField(blank=True)
    confidential_to_editor = models.TextField(blank=True)
    recommendation = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_CHOICES,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reviews_review"

    def __str__(self):
        return f"Review for {self.assignment.submission.title}"

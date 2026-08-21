"""Tests for review workflow."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from journals.models import MEMBERSHIP_STATUS_APPROVED
from reviews.models import Review, ReviewAssignment, STATUS_ACCEPTED, STATUS_INVITED, STATUS_REVIEW_SUBMITTED
from submissions.models import Submission, SubmissionVersion, TopicArea
from tests.helpers import make_journal, make_membership

_email_counter = [0]


def make_user(roles, journal, reviewer_status=None, editor_status=None):
    """Create user with roles and approval."""
    _email_counter[0] += 1
    user = User.objects.create_user(
        email=f"user_{_email_counter[0]}@test.com",
        password="testpass123",
        full_name="User",
        is_email_verified=True,
    )
    for role in roles:
        status_ = MEMBERSHIP_STATUS_APPROVED
        if role == "reviewer" and reviewer_status:
            status_ = reviewer_status
        if role == "editor" and editor_status:
            status_ = editor_status
        make_membership(user, journal, role, status=status_)
    return user


class ReviewWorkflowTest(TestCase):
    """Test invite, accept, submit review."""

    def setUp(self):
        self.client = APIClient()
        self.journal = make_journal()
        self.base = f"/api/j/{self.journal.slug}"
        self.editor = make_user(["editor"], self.journal, editor_status=MEMBERSHIP_STATUS_APPROVED)
        self.reviewer = make_user(["reviewer"], self.journal, reviewer_status=MEMBERSHIP_STATUS_APPROVED)
        self.author = make_user(["author"], self.journal)
        self.topic = TopicArea.objects.create(journal=self.journal, name="AI", slug="ai")

        self.submission = Submission.objects.create(
            author=self.author,
            journal=self.journal,
            status="under_review",
            title="Paper",
            abstract="Abstract",
            keywords=["k1", "k2", "k3"],
            topic_area=self.topic,
        )
        pdf = SimpleUploadedFile("manuscript.pdf", b"pdf content", content_type="application/pdf")
        self.version = SubmissionVersion.objects.create(
            submission=self.submission,
            version_number=1,
            manuscript_pdf=pdf,
            supplementary_files_snapshot=[],
        )

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def test_invite_reviewer(self):
        self._login(self.editor)
        resp = self.client.post(
            f"{self.base}/editor/submissions/{self.submission.id}/invite-reviewer/",
            {"reviewer_user_id": self.reviewer.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", resp.data)
        assign = ReviewAssignment.objects.get(submission=self.submission)
        self.assertEqual(assign.status, STATUS_INVITED)
        self.assertEqual(assign.reviewer, self.reviewer)

    def test_accept_invitation(self):
        assign = ReviewAssignment.objects.create(
            submission=self.submission,
            submission_version=self.version,
            reviewer=self.reviewer,
            invited_email=self.reviewer.email,
            status=STATUS_INVITED,
        )
        self._login(self.reviewer)
        resp = self.client.post(f"{self.base}/reviewer/assignments/{assign.id}/accept/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        assign.refresh_from_db()
        self.assertEqual(assign.status, STATUS_ACCEPTED)

    def test_submit_review(self):
        assign = ReviewAssignment.objects.create(
            submission=self.submission,
            submission_version=self.version,
            reviewer=self.reviewer,
            invited_email=self.reviewer.email,
            status=STATUS_ACCEPTED,
        )
        self._login(self.reviewer)
        resp = self.client.post(
            f"{self.base}/reviewer/assignments/{assign.id}/submit-review/",
            {
                "summary": "Good paper",
                "strengths": "Clear",
                "weaknesses": "None",
                "recommendation": "accept",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        assign.refresh_from_db()
        self.assertEqual(assign.status, STATUS_REVIEW_SUBMITTED)
        Review.objects.get(assignment=assign)

    def test_submit_review_reject(self):
        assign = ReviewAssignment.objects.create(
            submission=self.submission,
            submission_version=self.version,
            reviewer=self.reviewer,
            invited_email=self.reviewer.email,
            status=STATUS_ACCEPTED,
        )
        self._login(self.reviewer)
        resp = self.client.post(
            f"{self.base}/reviewer/assignments/{assign.id}/submit-review/",
            {
                "summary": "Needs work",
                "strengths": "Topic is relevant",
                "weaknesses": "Method is weak",
                "recommendation": "reject",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        assign.refresh_from_db()
        self.assertEqual(assign.status, STATUS_REVIEW_SUBMITTED)

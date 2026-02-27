"""Tests for review workflow."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import APPROVAL_APPROVED, User
from reviews.models import ReviewAssignment, STATUS_ACCEPTED, STATUS_INVITED, STATUS_REVIEW_SUBMITTED
from submissions.models import Submission, SubmissionVersion, TopicArea


def make_user(roles, reviewer_status=None, editor_status=None):
    """Create user with roles and approval."""
    role_str = "_".join(roles)
    user = User.objects.create_user(
        email=f"user_{role_str}_{id(roles)}@test.com",
        password="testpass123",
        full_name="User",
        roles=roles,
    )
    if reviewer_status:
        user.reviewer_status = reviewer_status
    if editor_status:
        user.editor_status = editor_status
    user.save()
    return user


class ReviewWorkflowTest(TestCase):
    """Test invite, accept, submit review."""

    def setUp(self):
        self.client = APIClient()
        self.editor = make_user(["editor"], editor_status=APPROVAL_APPROVED)
        self.reviewer = make_user(["reviewer"], reviewer_status=APPROVAL_APPROVED)
        self.author = make_user(["author"])
        self.topic = TopicArea.objects.create(name="AI", slug="ai")

        self.submission = Submission.objects.create(
            author=self.author,
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
            f"/api/editor/submissions/{self.submission.id}/invite-reviewer/",
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
        resp = self.client.post(f"/api/reviewer/assignments/{assign.id}/accept/")
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
            f"/api/reviewer/assignments/{assign.id}/submit-review/",
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

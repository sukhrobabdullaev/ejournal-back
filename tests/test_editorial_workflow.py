"""Tests for editorial workflow."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import APPROVAL_APPROVED, User
from submissions.models import STATUS_DESK_REJECTED, STATUS_SCREENING, STATUS_SUBMITTED, Submission, SubmissionVersion, TopicArea


def make_user(roles, editor_status=None):
    """Create user with editor approval."""
    user = User.objects.create_user(
        email=f"editor_{id(roles)}@test.com",
        password="testpass123",
        full_name="Editor",
        roles=roles,
    )
    if editor_status:
        user.editor_status = editor_status
        user.save()
    return user


class EditorialWorkflowTest(TestCase):
    """Test screening, desk reject, decision, publish."""

    def setUp(self):
        self.client = APIClient()
        self.editor = make_user(["editor"], editor_status=APPROVAL_APPROVED)
        self.author = make_user(["author"])
        self.topic = TopicArea.objects.create(name="AI", slug="ai")

        self.submission = Submission.objects.create(
            author=self.author,
            status=STATUS_SUBMITTED,
            title="Paper",
            abstract="Abstract",
            keywords=["k1", "k2", "k3"],
            topic_area=self.topic,
        )

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def test_start_screening(self):
        self._login(self.editor)
        resp = self.client.post(f"/api/editor/submissions/{self.submission.id}/start-screening/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, STATUS_SCREENING)

    def test_desk_reject(self):
        self.submission.status = STATUS_SCREENING
        self.submission.save()
        self._login(self.editor)
        resp = self.client.post(
            f"/api/editor/submissions/{self.submission.id}/desk-reject/",
            {"reason": "Out of scope"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, STATUS_DESK_REJECTED)
        self.assertEqual(self.submission.desk_reject_reason, "Out of scope")

    def test_decision_accept(self):
        pdf = SimpleUploadedFile("manuscript.pdf", b"pdf", content_type="application/pdf")
        SubmissionVersion.objects.create(
            submission=self.submission,
            version_number=1,
            manuscript_pdf=pdf,
            supplementary_files_snapshot=[],
        )
        self.submission.status = "decision_pending"
        self.submission.save()
        self._login(self.editor)
        resp = self.client.post(
            f"/api/editor/submissions/{self.submission.id}/decision/",
            {"decision": "accept", "decision_letter": "We are pleased to accept."},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, "accepted")

    def test_publish(self):
        self.submission.status = "accepted"
        self.submission.save()
        self._login(self.editor)
        resp = self.client.post(f"/api/editor/submissions/{self.submission.id}/publish/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, "published")

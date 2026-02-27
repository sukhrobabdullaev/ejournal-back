"""Tests for submission workflow (author)."""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from submissions.models import Submission, TopicArea


def make_author():
    """Create author user."""
    return User.objects.create_user(
        email="author@test.com",
        password="testpass123",
        full_name="Author",
        roles=["author"],
    )


class SubmissionWorkflowTest(TestCase):
    """Test submission create, partial save, submit validation."""

    def setUp(self):
        self.client = APIClient()
        self.author = make_author()
        self.topic = TopicArea.objects.create(name="AI", slug="ai")

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def test_create_draft(self):
        self._login(self.author)
        resp = self.client.post("/api/submissions/", {})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "draft")
        self.assertEqual(Submission.objects.filter(author=self.author).count(), 1)

    def test_submit_without_required_fields_fails(self):
        self._login(self.author)
        resp = self.client.post("/api/submissions/", {})
        sub_id = resp.data["id"]
        resp = self.client.post(f"/api/submissions/{sub_id}/submit/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_partial_save(self):
        self._login(self.author)
        resp = self.client.post("/api/submissions/", {})
        sub_id = resp.data["id"]
        resp = self.client.patch(
            f"/api/submissions/{sub_id}/",
            {"title": "My Paper", "abstract": "Abstract here", "keywords": ["a", "b", "c"], "topic_area_id": self.topic.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["title"], "My Paper")

    def test_submit_requires_agreements(self):
        self._login(self.author)
        resp = self.client.post("/api/submissions/", {})
        sub_id = resp.data["id"]
        Submission.objects.filter(id=sub_id).update(
            title="Title",
            abstract="Abstract",
            keywords=["k1", "k2", "k3"],
            topic_area=self.topic,
            originality_confirmation=True,
            plagiarism_agreement=True,
            ethics_compliance=False,  # Missing
            copyright_agreement=True,
        )
        resp = self.client.post(f"/api/submissions/{sub_id}/submit/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

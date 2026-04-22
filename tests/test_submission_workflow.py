"""Tests for submission workflow (author)."""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
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
        is_email_verified=True,
        orcid_id="0000-0002-1234-5678",
        google_scholar_url="https://scholar.google.com/citations?user=AUTHOR123",
    )

def make_reviewer():
    """Create reviewer-only user."""
    return User.objects.create_user(
        email="reviewer_only@test.com",
        password="testpass123",
        full_name="Reviewer Only",
        roles=["reviewer"],
        is_email_verified=True,
    )


class SubmissionWorkflowTest(TestCase):
    """Test submission create, partial save, submit validation."""

    def setUp(self):
        self.client = APIClient()
        self.author = make_author()
        self.reviewer = make_reviewer()
        self.topic = TopicArea.objects.create(name="AI", slug="ai")

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def test_create_submission_defaults_to_submitted(self):
        self._login(self.author)
        resp = self.client.post("/api/submissions/", {})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "submitted")
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

    def test_non_author_cannot_create_submission(self):
        self._login(self.reviewer)
        resp = self.client.post("/api/submissions/", {})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_submit_requires_author_orcid_profile(self):
        self.author.orcid_id = ""
        self.author.save(update_fields=["orcid_id"])

        submission = Submission.objects.create(
            author=self.author,
            status="submitted",
            title="Profile check",
            abstract="Abstract",
            keywords=["k1", "k2", "k3"],
            topic_area=self.topic,
            originality_confirmation=True,
            plagiarism_agreement=True,
            ethics_compliance=True,
            copyright_agreement=True,
            manuscript_pdf=SimpleUploadedFile("paper.pdf", b"pdf", content_type="application/pdf"),
        )

        self._login(self.author)
        resp = self.client.post(f"/api/submissions/{submission.id}/submit/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ORCID", str(resp.data))

    def test_submit_requires_author_google_scholar_profile(self):
        self.author.google_scholar_url = ""
        self.author.save(update_fields=["google_scholar_url"])

        submission = Submission.objects.create(
            author=self.author,
            status="submitted",
            title="Scholar check",
            abstract="Abstract",
            keywords=["k1", "k2", "k3"],
            topic_area=self.topic,
            originality_confirmation=True,
            plagiarism_agreement=True,
            ethics_compliance=True,
            copyright_agreement=True,
            manuscript_pdf=SimpleUploadedFile("paper.pdf", b"pdf", content_type="application/pdf"),
        )

        self._login(self.author)
        resp = self.client.post(f"/api/submissions/{submission.id}/submit/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Google Scholar", str(resp.data))

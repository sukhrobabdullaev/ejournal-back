"""Tests for ORCID profile updates via /api/me."""
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User


class OrcidProfileApiTest(TestCase):
    """Validate ORCID update behavior on authenticated profile endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="author@test.com",
            password="testpass123",
            full_name="Author User",
            roles=["author"],
        )
        self.client.force_authenticate(user=self.user)

    def test_patch_me_accepts_valid_orcid_and_normalizes(self):
        response = self.client.patch(
            "/api/me",
            {"orcid_id": "0000-0002-1234-5678"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.orcid_id, "0000-0002-1234-5678")

    def test_patch_me_rejects_invalid_orcid(self):
        response = self.client.patch(
            "/api/me",
            {"orcid_id": "bad-orcid"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("orcid_id", response.data)

    def test_patch_me_allows_clearing_orcid(self):
        self.user.orcid_id = "0000-0002-1234-5678"
        self.user.save(update_fields=["orcid_id"])

        response = self.client.patch(
            "/api/me",
            {"orcid_id": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.orcid_id, "")

    def test_patch_me_accepts_valid_google_scholar_url(self):
        response = self.client.patch(
            "/api/me",
            {"google_scholar_url": "https://scholar.google.com/citations?user=XYZ123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(
            self.user.google_scholar_url,
            "https://scholar.google.com/citations?user=XYZ123",
        )

    def test_patch_me_rejects_invalid_google_scholar_url(self):
        response = self.client.patch(
            "/api/me",
            {"google_scholar_url": "https://example.com/profile"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("google_scholar_url", response.data)

    def test_patch_me_allows_clearing_google_scholar_url(self):
        self.user.google_scholar_url = "https://scholar.google.com/citations?user=ABCD"
        self.user.save(update_fields=["google_scholar_url"])

        response = self.client.patch(
            "/api/me",
            {"google_scholar_url": ""},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.google_scholar_url, "")

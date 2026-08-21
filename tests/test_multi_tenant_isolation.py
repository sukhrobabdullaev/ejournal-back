"""Tests for cross-journal data and permission isolation."""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from journals.models import MEMBERSHIP_STATUS_APPROVED
from submissions.models import JournalIssue, Submission, TopicArea
from tests.helpers import make_journal, make_membership


class MultiTenantIsolationTest(TestCase):
    """A user can hold different roles in different journals, and journal data never leaks across tenants."""

    def setUp(self):
        self.client = APIClient()
        self.journal_a = make_journal(slug="journal-a", name="Journal A")
        self.journal_b = make_journal(slug="journal-b", name="Journal B")

        self.user = User.objects.create_user(
            email="dual@test.com", password="testpass123", full_name="Dual Role User", is_email_verified=True
        )
        make_membership(self.user, self.journal_a, "editor", status=MEMBERSHIP_STATUS_APPROVED)
        make_membership(self.user, self.journal_b, "author", status=MEMBERSHIP_STATUS_APPROVED)

        self.topic_a = TopicArea.objects.create(journal=self.journal_a, name="AI", slug="ai")
        JournalIssue.objects.create(
            journal=self.journal_a, title="A Issue 1", volume=1, issue_number=1, publication_year=2026
        )

    def test_unknown_journal_slug_404s(self):
        response = self.client.get("/api/j/does-not-exist/published/issues/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_published_issues_isolated_per_journal(self):
        resp_a = self.client.get(f"/api/j/{self.journal_a.slug}/published/issues/")
        resp_b = self.client.get(f"/api/j/{self.journal_b.slug}/published/issues/")
        self.assertEqual(resp_a.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_b.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_a.data), 0)
        self.assertEqual(len(resp_b.data), 0)

    def test_editor_role_in_journal_a_does_not_grant_editor_in_journal_b(self):
        self.client.force_authenticate(user=self.user)

        resp_a = self.client.get(f"/api/j/{self.journal_a.slug}/editor/submissions/")
        self.assertEqual(resp_a.status_code, status.HTTP_200_OK)

        resp_b = self.client.get(f"/api/j/{self.journal_b.slug}/editor/submissions/")
        self.assertEqual(resp_b.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_role_in_journal_b_allows_submission_there_only(self):
        self.client.force_authenticate(user=self.user)

        resp_b = self.client.post(f"/api/j/{self.journal_b.slug}/submissions/", {})
        self.assertEqual(resp_b.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Submission.objects.get(id=resp_b.data["id"]).journal_id, self.journal_b.id)

        resp_a = self.client.post(f"/api/j/{self.journal_a.slug}/submissions/", {})
        self.assertEqual(resp_a.status_code, status.HTTP_403_FORBIDDEN)

    def test_topic_areas_scoped_to_journal(self):
        self.client.force_authenticate(user=self.user)
        resp_a = self.client.get(f"/api/j/{self.journal_a.slug}/topic-areas/")
        resp_b = self.client.get(f"/api/j/{self.journal_b.slug}/topic-areas/")
        self.assertEqual(resp_a.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_b.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_a.data), 1)
        self.assertEqual(len(resp_b.data), 0)

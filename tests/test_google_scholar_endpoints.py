"""Tests for Google Scholar crawlable endpoints."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils.text import slugify
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from submissions.models import JournalIssue, STATUS_ACCEPTED, STATUS_PUBLISHED, Submission, TopicArea


def _build_slug(submission: Submission) -> str:
    base = slugify(submission.title or "")[:80] or "article"
    return f"{base}-{submission.id}"


class GoogleScholarEndpointsTest(TestCase):
    """Ensure Scholar-specific HTML endpoints expose crawlable metadata."""

    def setUp(self):
        self.client = APIClient()
        self.author = User.objects.create_user(
            email="author-scholar@test.com",
            password="testpass123",
            full_name="Scholar Author",
            roles=["author"],
            is_email_verified=True,
            affiliation="Ditech Asia",
            orcid_id="0000-0002-1234-5678",
            google_scholar_url="https://scholar.google.com/citations?user=AUTHOR123",
        )
        self.topic = TopicArea.objects.create(name="AI", slug="ai-scholar")
        self.issue = JournalIssue.objects.create(
            title="Volume 10 Issue 1",
            volume=10,
            issue_number=1,
            publication_year=2026,
            publication_date="2026-04-22",
        )

        self.published_submission = Submission.objects.create(
            author=self.author,
            status=STATUS_PUBLISHED,
            title="Scholar Ready Article",
            abstract="This is a machine-readable abstract for indexing.",
            keywords=["ai", "indexing", "metadata"],
            topic_area=self.topic,
            manuscript_pdf=SimpleUploadedFile("paper.pdf", b"pdf", content_type="application/pdf"),
            issue=self.issue,
            issue_order=1,
            page_start=1,
            page_end=8,
            doi="10.5555/ejournal.v10.i1.a1",
        )

        self.unpublished_submission = Submission.objects.create(
            author=self.author,
            status=STATUS_ACCEPTED,
            title="Not Published Yet",
            abstract="Hidden from scholar sitemap",
            keywords=["hidden"],
            topic_area=self.topic,
        )

    def test_scholar_article_landing_contains_citation_meta(self):
        slug = _build_slug(self.published_submission)
        response = self.client.get(f"/api/scholar/articles/{slug}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["X-Robots-Tag"], "index, follow")

        html = response.content.decode("utf-8")
        self.assertIn('name="citation_title"', html)
        self.assertIn('name="citation_author"', html)
        self.assertIn('name="citation_journal_title"', html)
        self.assertIn('name="citation_publication_date"', html)
        self.assertIn('name="citation_doi"', html)
        self.assertIn('name="citation_pdf_url"', html)
        self.assertIn('name="citation_abstract_html_url"', html)
        self.assertIn('name="citation_fulltext_html_url"', html)
        self.assertIn(self.published_submission.title, html)

    def test_scholar_sitemap_lists_only_published_articles(self):
        response = self.client.get("/api/scholar/sitemap.xml")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode("utf-8")
        self.assertIn("/api/scholar/articles/", content)
        self.assertIn(_build_slug(self.published_submission), content)
        self.assertNotIn(_build_slug(self.unpublished_submission), content)

    def test_scholar_robots_references_sitemap(self):
        response = self.client.get("/api/scholar/robots.txt")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.content.decode("utf-8")
        self.assertIn("User-agent: *", body)
        self.assertIn("Sitemap:", body)
        self.assertIn("/api/scholar/sitemap.xml", body)

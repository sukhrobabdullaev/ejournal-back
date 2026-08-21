"""Tests for issue publishing and merged PDF endpoints."""
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from PyPDF2 import PdfReader, PdfWriter

from accounts.models import User
from journals.models import MEMBERSHIP_STATUS_APPROVED
from submissions.models import DOI_STATUS_PENDING, JournalIssue, STATUS_ACCEPTED, STATUS_PUBLISHED, Submission, TopicArea
from tests.helpers import make_journal, make_membership


def make_pdf_file(filename: str, pages: int = 1) -> SimpleUploadedFile:
    """Create a minimal valid PDF file for tests."""
    writer = PdfWriter()
    for _ in range(max(1, pages)):
        writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return SimpleUploadedFile(filename, buffer.getvalue(), content_type="application/pdf")


def make_user(email: str, roles: list[str], journal, editor_status: str | None = None):
    user = User.objects.create_user(
        email=email,
        password="testpass123",
        full_name=email.split("@")[0].title(),
        is_email_verified=True,
    )
    for role in roles:
        status_ = editor_status if (role == "editor" and editor_status) else MEMBERSHIP_STATUS_APPROVED
        make_membership(user, journal, role, status=status_)
    return user


class JournalIssueWorkflowTest(TestCase):
    """Issue creation and public access tests."""

    def setUp(self):
        self.client = APIClient()
        self.journal = make_journal()
        self.base = f"/api/j/{self.journal.slug}"
        self.editor = make_user("editor@test.com", ["editor"], self.journal, editor_status=MEMBERSHIP_STATUS_APPROVED)
        self.author = make_user("author@test.com", ["author"], self.journal)
        self.topic = TopicArea.objects.create(journal=self.journal, name="AI", slug="ai")

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def _create_accepted_submission(self, title: str, filename: str, pages: int = 1) -> Submission:
        return Submission.objects.create(
            author=self.author,
            journal=self.journal,
            status=STATUS_ACCEPTED,
            title=title,
            abstract="Abstract",
            keywords=["ai", "ml", "nlp"],
            topic_area=self.topic,
            manuscript_pdf=make_pdf_file(filename, pages=pages),
        )

    def test_editor_can_publish_issue_and_merge_pdfs(self):
        submission_1 = self._create_accepted_submission("Paper 1", "paper_1.pdf")
        submission_2 = self._create_accepted_submission("Paper 2", "paper_2.pdf")
        self._login(self.editor)

        response = self.client.post(
            f"{self.base}/editor/issues/",
            {
                "title": "Volume 5 Issue 2",
                "volume": 5,
                "issue_number": 2,
                "publication_year": 2026,
                "articles": [
                    {
                        "submission_id": submission_1.id,
                        "order": 1,
                        "page_start": 1,
                        "page_end": 6,
                    },
                    {
                        "submission_id": submission_2.id,
                        "order": 2,
                        "page_start": 7,
                        "page_end": 15,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        issue = JournalIssue.objects.get(journal=self.journal, volume=5, issue_number=2, publication_year=2026)
        self.assertTrue(bool(issue.full_issue_pdf))
        issue.full_issue_pdf.open("rb")
        try:
            merged_reader = PdfReader(issue.full_issue_pdf)
            self.assertEqual(len(merged_reader.pages), 3)  # cover + 2 article PDFs
            cover_size = (
                int(float(merged_reader.pages[0].mediabox.width)),
                int(float(merged_reader.pages[0].mediabox.height)),
            )
            article_page_size = (
                int(float(merged_reader.pages[1].mediabox.width)),
                int(float(merged_reader.pages[1].mediabox.height)),
            )
            self.assertEqual(cover_size, article_page_size)
        finally:
            issue.full_issue_pdf.close()

        submission_1.refresh_from_db()
        submission_2.refresh_from_db()
        self.assertEqual(submission_1.status, STATUS_PUBLISHED)
        self.assertEqual(submission_1.issue_id, issue.id)
        self.assertEqual(submission_1.issue_order, 1)
        self.assertEqual(submission_1.page_start, 1)
        self.assertEqual(submission_1.page_end, 1)
        self.assertTrue(submission_1.doi)
        self.assertEqual(submission_1.doi_status, DOI_STATUS_PENDING)

        self.assertEqual(submission_2.status, STATUS_PUBLISHED)
        self.assertEqual(submission_2.issue_id, issue.id)
        self.assertEqual(submission_2.issue_order, 2)
        self.assertEqual((submission_2.page_start, submission_2.page_end), (2, 2))
        self.assertTrue(submission_2.doi)
        self.assertEqual(submission_2.doi_status, DOI_STATUS_PENDING)

    @patch("notifications.tasks.send_issue_author_journal_certificate_emails.delay")
    def test_make_journal_queues_author_certificate_task(self, mocked_delay):
        submission = self._create_accepted_submission("Paper Queue Test", "queue-test.pdf")
        self._login(self.editor)

        response = self.client.post(
            f"{self.base}/editor/issues/",
            {
                "title": "Volume 6 Issue 1",
                "volume": 6,
                "issue_number": 1,
                "publication_year": 2026,
                "articles": [
                    {
                        "submission_id": submission.id,
                        "order": 1,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        issue_id = response.data["id"]
        mocked_delay.assert_called_once_with(issue_id)

    def test_public_published_issues_endpoints(self):
        issue = JournalIssue.objects.create(
            journal=self.journal,
            title="Volume 3 Issue 1",
            volume=3,
            issue_number=1,
            publication_year=2025,
            full_issue_pdf=make_pdf_file("full_issue.pdf"),
        )
        submission = Submission.objects.create(
            author=self.author,
            journal=self.journal,
            status=STATUS_PUBLISHED,
            title="Published paper",
            abstract="Public abstract",
            keywords=["data", "science", "analysis"],
            topic_area=self.topic,
            manuscript_pdf=make_pdf_file("published_article.pdf"),
            issue=issue,
            issue_order=1,
            page_start=1,
            page_end=10,
        )

        list_response = self.client.get(f"{self.base}/published/issues/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["id"], issue.id)

        detail_response = self.client.get(f"{self.base}/published/issues/{issue.id}/")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["id"], issue.id)
        self.assertEqual(len(detail_response.data["articles"]), 1)
        self.assertEqual(detail_response.data["articles"][0]["id"], submission.id)
        self.assertEqual(detail_response.data["articles"][0]["page_start"], 1)
        self.assertEqual(detail_response.data["articles"][0]["page_end"], 10)

    def test_editor_can_update_existing_issue(self):
        self._login(self.editor)
        submission_1 = self._create_accepted_submission("Initial paper", "initial.pdf")
        submission_2 = self._create_accepted_submission("Second paper", "second.pdf")

        create_response = self.client.post(
            f"{self.base}/editor/issues/",
            {
                "title": "Issue A",
                "volume": 7,
                "issue_number": 1,
                "publication_year": 2026,
                "articles": [
                    {
                        "submission_id": submission_1.id,
                        "order": 1,
                        "page_start": 1,
                        "page_end": 5,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        issue_id = create_response.data["id"]

        update_response = self.client.put(
            f"{self.base}/editor/issues/{issue_id}/",
            {
                "title": "Issue A Updated",
                "volume": 7,
                "issue_number": 1,
                "publication_year": 2026,
                "articles": [
                    {
                        "submission_id": submission_1.id,
                        "order": 1,
                        "page_start": 1,
                        "page_end": 5,
                    },
                    {
                        "submission_id": submission_2.id,
                        "order": 2,
                        "page_start": 6,
                        "page_end": 12,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["title"], "Issue A Updated")
        self.assertEqual(len(update_response.data["articles"]), 2)

        submission_2.refresh_from_db()
        self.assertEqual(submission_2.status, STATUS_PUBLISHED)
        self.assertEqual(submission_2.issue_id, issue_id)

    def test_accepted_submissions_endpoint_includes_published_status(self):
        self._login(self.editor)
        accepted_submission = self._create_accepted_submission("Accepted one", "accepted.pdf")
        published_submission = Submission.objects.create(
            author=self.author,
            journal=self.journal,
            status=STATUS_PUBLISHED,
            title="Published one",
            abstract="Abstract",
            keywords=["k1", "k2", "k3"],
            topic_area=self.topic,
            manuscript_pdf=make_pdf_file("published.pdf"),
        )

        response = self.client.get(f"{self.base}/editor/issues/accepted-submissions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ids = {item["id"] for item in response.data}
        self.assertIn(accepted_submission.id, ids)
        self.assertIn(published_submission.id, ids)

    def test_accepted_submissions_endpoint_hides_already_assigned_articles(self):
        self._login(self.editor)
        available_submission = self._create_accepted_submission("Available", "available.pdf")
        assigned_submission = self._create_accepted_submission("Assigned", "assigned.pdf")
        issue = JournalIssue.objects.create(
            journal=self.journal,
            title="Existing issue",
            volume=11,
            issue_number=1,
            publication_year=2026,
            full_issue_pdf=make_pdf_file("existing_issue.pdf"),
        )
        assigned_submission.issue = issue
        assigned_submission.issue_order = 1
        assigned_submission.page_start = 1
        assigned_submission.page_end = 1
        assigned_submission.status = STATUS_PUBLISHED
        assigned_submission.save(
            update_fields=["issue", "issue_order", "page_start", "page_end", "status", "updated_at"]
        )

        response = self.client.get(f"{self.base}/editor/issues/accepted-submissions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ids = {item["id"] for item in response.data}
        self.assertIn(available_submission.id, ids)
        self.assertNotIn(assigned_submission.id, ids)

    def test_editor_can_publish_issue_with_publication_date(self):
        self._login(self.editor)
        submission = self._create_accepted_submission("Dated issue paper", "dated.pdf")

        response = self.client.post(
            f"{self.base}/editor/issues/",
            {
                "title": "Dated Issue",
                "volume": 8,
                "issue_number": 2,
                "publication_date": "2026-03-28",
                "articles": [
                    {
                        "submission_id": submission.id,
                        "order": 1,
                        "page_start": 1,
                        "page_end": 4,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        issue = JournalIssue.objects.get(id=response.data["id"])
        self.assertEqual(str(issue.publication_date), "2026-03-28")
        self.assertEqual(issue.publication_year, 2026)

    def test_issue_pagination_auto_follows_pdf_page_count(self):
        self._login(self.editor)
        submission_1 = self._create_accepted_submission("Paper A", "a.pdf", pages=6)
        submission_2 = self._create_accepted_submission("Paper B", "b.pdf", pages=4)

        response = self.client.post(
            f"{self.base}/editor/issues/",
            {
                "title": "Auto Pagination Issue",
                "volume": 9,
                "issue_number": 1,
                "publication_year": 2026,
                "articles": [
                    {"submission_id": submission_1.id, "order": 1},
                    {"submission_id": submission_2.id, "order": 2},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        submission_1.refresh_from_db()
        submission_2.refresh_from_db()
        self.assertEqual((submission_1.page_start, submission_1.page_end), (1, 6))
        self.assertEqual((submission_2.page_start, submission_2.page_end), (7, 10))

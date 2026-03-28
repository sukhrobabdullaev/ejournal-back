"""Tests for journal publication certificate email task and PDF builder."""
from datetime import date

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from notifications.certificates import build_journal_publication_certificate_pdf
from notifications.models import JournalPublicationCertificate
from notifications.tasks import send_issue_author_journal_certificate_emails
from submissions.models import JournalIssue, STATUS_PUBLISHED, Submission, TopicArea


def make_user(email: str, roles: list[str]):
    return User.objects.create_user(
        email=email,
        password="testpass123",
        full_name=email.split("@")[0].title(),
        roles=roles,
    )


class JournalCertificateTaskTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.author = make_user("author_journal@test.com", ["author"])
        self.topic = TopicArea.objects.create(name="AI", slug="ai")
        self.issue = JournalIssue.objects.create(
            title="Volume 4, Issue 2 (2026)",
            volume=4,
            issue_number=2,
            publication_year=2026,
            publication_date=date(2026, 3, 28),
        )
        self.submission = Submission.objects.create(
            author=self.author,
            status=STATUS_PUBLISHED,
            title="AI for Smart Editorial Workflow",
            abstract="Abstract",
            keywords=["ai", "editorial", "workflow"],
            topic_area=self.topic,
            manuscript_pdf=SimpleUploadedFile("article.pdf", b"dummy-pdf", content_type="application/pdf"),
            issue=self.issue,
            issue_order=1,
            page_start=1,
            page_end=6,
        )

    def test_pdf_builder_returns_pdf_bytes(self):
        content = build_journal_publication_certificate_pdf(
            author_full_name=self.author.full_name,
            article_title=self.submission.title,
            issue_title=self.issue.title,
            volume=self.issue.volume,
            issue_number=self.issue.issue_number,
            publication_year=self.issue.publication_year,
            publication_date=self.issue.publication_date,
            author_affiliation="Ditech Asia",
            author_country="Uzbekistan",
            certificate_code="demo-code",
        )
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 1500)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_task_sends_journal_certificate_email_once(self):
        result = send_issue_author_journal_certificate_emails(self.issue.id)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to, [self.author.email])
        self.assertIn("Journal Certificate", email.subject)
        self.assertEqual(len(email.attachments), 1)
        filename, content, mimetype = email.attachments[0]
        self.assertTrue(filename.endswith(".pdf"))
        self.assertEqual(mimetype, "application/pdf")
        self.assertTrue(content.startswith(b"%PDF"))

        certificate = JournalPublicationCertificate.objects.get(
            issue=self.issue,
            submission=self.submission,
            author=self.author,
        )
        self.assertIsNotNone(certificate.email_sent_at)

        second_result = send_issue_author_journal_certificate_emails(self.issue.id)
        self.assertEqual(second_result["status"], "completed")
        self.assertEqual(second_result["sent"], 0)
        self.assertEqual(second_result["skipped"], 1)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_submission_payload_includes_journal_certificates(self):
        task_result = send_issue_author_journal_certificate_emails(self.issue.id)
        self.client.force_authenticate(user=self.author)

        response = self.client.get("/api/submissions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIn("journal_certificates", response.data[0])
        self.assertEqual(len(response.data[0]["journal_certificates"]), 1)
        code = task_result["results"][0]["certificate_id"]
        self.assertIsNotNone(code)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_journal_certificate_public_endpoints(self):
        send_issue_author_journal_certificate_emails(self.issue.id)
        certificate = JournalPublicationCertificate.objects.get(
            issue=self.issue,
            submission=self.submission,
            author=self.author,
        )

        detail = self.client.get(f"/api/certificates/journal/public/{certificate.verification_code}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["submission_id"], self.submission.id)

        pdf = self.client.get(f"/api/certificates/journal/public/{certificate.verification_code}/pdf/")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")

        qr = self.client.get(f"/api/certificates/journal/public/{certificate.verification_code}/qr.svg")
        self.assertEqual(qr.status_code, 200)
        self.assertEqual(qr["Content-Type"], "image/svg+xml")

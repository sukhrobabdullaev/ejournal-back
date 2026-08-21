"""Tests for reviewer recognition certificate task and PDF builder."""
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from accounts.models import User
from journals.models import MEMBERSHIP_STATUS_APPROVED
from notifications.certificates import build_reviewer_recognition_pdf
from notifications.models import ReviewerRecognitionCertificate
from notifications.tasks import send_author_reviewer_recognition_certificate
from reviews.models import RECOMMENDATION_ACCEPT, RECOMMENDATION_REJECT, Review, ReviewAssignment, STATUS_ACCEPTED
from submissions.models import STATUS_ACCEPTED as SUBMISSION_STATUS_ACCEPTED
from submissions.models import Submission, SubmissionVersion, TopicArea
from tests.helpers import make_journal, make_membership

_email_counter = [0]


def make_user(roles, journal, reviewer_status=None):
    _email_counter[0] += 1
    user = User.objects.create_user(
        email=f"user_{_email_counter[0]}@test.com",
        password="testpass123",
        full_name="Test User",
        is_email_verified=True,
    )
    for role in roles:
        status_ = reviewer_status if (role == "reviewer" and reviewer_status) else MEMBERSHIP_STATUS_APPROVED
        make_membership(user, journal, role, status=status_)
    return user


class ReviewerCertificateTaskTest(TestCase):
    def setUp(self):
        self.journal = make_journal()
        self.author = make_user(["author"], self.journal)
        self.reviewer = make_user(["reviewer"], self.journal, reviewer_status=MEMBERSHIP_STATUS_APPROVED)
        self.topic = TopicArea.objects.create(journal=self.journal, name="AI", slug="ai")
        self.submission = Submission.objects.create(
            author=self.author,
            journal=self.journal,
            status="under_review",
            title="Large Language Models for Journal Automation",
            abstract="Abstract",
            keywords=["llm", "automation", "journal"],
            topic_area=self.topic,
        )
        pdf = SimpleUploadedFile("paper.pdf", b"pdf content", content_type="application/pdf")
        self.version = SubmissionVersion.objects.create(
            submission=self.submission,
            version_number=1,
            manuscript_pdf=pdf,
            supplementary_files_snapshot=[],
        )
        self.assignment = ReviewAssignment.objects.create(
            submission=self.submission,
            submission_version=self.version,
            reviewer=self.reviewer,
            invited_email=self.reviewer.email,
            status=STATUS_ACCEPTED,
        )

    def test_pdf_builder_returns_pdf_bytes(self):
        content = build_reviewer_recognition_pdf(
            submission_title=self.submission.title,
            author_full_name=self.author.full_name,
            reviewer_full_name=self.reviewer.full_name,
        )
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 1500)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_task_sends_email_with_pdf_attachment_for_accept(self):
        review = Review.objects.create(
            assignment=self.assignment,
            summary="Excellent",
            strengths="Novel and clear",
            weaknesses="Minor typos",
            confidential_to_editor="",
            recommendation=RECOMMENDATION_ACCEPT,
        )
        self.submission.status = SUBMISSION_STATUS_ACCEPTED
        self.submission.editorial_decision = "accept"
        self.submission.decision_letter = "Accepted after editorial evaluation."
        self.submission.save(update_fields=["status", "editorial_decision", "decision_letter"])

        result = send_author_reviewer_recognition_certificate(review.id)

        self.assertEqual(result["status"], "sent")
        self.assertIn("certificate_id", result)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.author.email])
        self.assertEqual(email.subject, "Reviewer Recognition Certificate")
        self.assertEqual(len(email.attachments), 1)
        filename, content, mimetype = email.attachments[0]
        self.assertTrue(filename.endswith(".pdf"))
        self.assertEqual(mimetype, "application/pdf")
        self.assertTrue(content.startswith(b"%PDF"))
        certificate = ReviewerRecognitionCertificate.objects.get(review=review)
        self.assertEqual(certificate.author_id, self.author.id)
        self.assertEqual(certificate.submission_id, self.submission.id)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_task_skips_when_editor_decision_is_not_accept(self):
        review = Review.objects.create(
            assignment=self.assignment,
            summary="Not enough",
            strengths="Interesting problem",
            weaknesses="Insufficient experiments",
            confidential_to_editor="",
            recommendation=RECOMMENDATION_REJECT,
        )
        self.submission.status = "decision_pending"
        self.submission.editorial_decision = "reject"
        self.submission.decision_letter = "Rejected by editor."
        self.submission.save(update_fields=["status", "editorial_decision", "decision_letter"])

        result = send_author_reviewer_recognition_certificate(review.id)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "editor_decision_not_accept")
        self.assertEqual(len(mail.outbox), 0)

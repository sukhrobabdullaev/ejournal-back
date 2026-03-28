"""Tests for reviewer recognition certificate task and PDF builder."""
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from accounts.models import APPROVAL_APPROVED, User
from notifications.certificates import build_reviewer_recognition_pdf
from notifications.models import ReviewerRecognitionCertificate
from notifications.tasks import send_author_reviewer_recognition_certificate
from reviews.models import RECOMMENDATION_ACCEPT, RECOMMENDATION_REJECT, Review, ReviewAssignment, STATUS_ACCEPTED
from submissions.models import STATUS_ACCEPTED as SUBMISSION_STATUS_ACCEPTED
from submissions.models import Submission, SubmissionVersion, TopicArea


def make_user(roles, reviewer_status=None):
    role_str = "_".join(roles)
    user = User.objects.create_user(
        email=f"{role_str}_{id(roles)}@test.com",
        password="testpass123",
        full_name=f"{role_str.title()} User",
        roles=roles,
    )
    if reviewer_status:
        user.reviewer_status = reviewer_status
        user.save(update_fields=["reviewer_status"])
    return user


class ReviewerCertificateTaskTest(TestCase):
    def setUp(self):
        self.author = make_user(["author"])
        self.reviewer = make_user(["reviewer"], reviewer_status=APPROVAL_APPROVED)
        self.topic = TopicArea.objects.create(name="AI", slug="ai")
        self.submission = Submission.objects.create(
            author=self.author,
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
        self.assertEqual(email.subject, "Reviewer recognize your article")
        self.assertIn("Reviewer comments:", email.body)
        self.assertIn("Editor comment:", email.body)
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

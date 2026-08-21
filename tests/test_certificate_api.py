"""Tests for certificate API endpoints and submission payload integration."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from journals.models import MEMBERSHIP_STATUS_APPROVED
from notifications.models import ReviewerRecognitionCertificate
from reviews.models import RECOMMENDATION_ACCEPT, Review, ReviewAssignment, STATUS_ACCEPTED
from submissions.models import Submission, SubmissionVersion, TopicArea
from tests.helpers import make_journal, make_membership

_email_counter = [0]


def make_user(roles, journal, reviewer_status=None):
    _email_counter[0] += 1
    user = User.objects.create_user(
        email=f"cert_{_email_counter[0]}@test.com",
        password="testpass123",
        full_name="Cert User",
        is_email_verified=True,
    )
    for role in roles:
        status_ = reviewer_status if (role == "reviewer" and reviewer_status) else MEMBERSHIP_STATUS_APPROVED
        make_membership(user, journal, role, status=status_)
    return user


class CertificateApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.journal = make_journal()
        self.base = f"/api/j/{self.journal.slug}"
        self.author = make_user(["author"], self.journal)
        self.reviewer = make_user(["reviewer"], self.journal, reviewer_status=MEMBERSHIP_STATUS_APPROVED)
        self.topic = TopicArea.objects.create(journal=self.journal, name="AI", slug="ai-cert")
        self.submission = Submission.objects.create(
            author=self.author,
            journal=self.journal,
            status="under_review",
            title="Transformer-Based Scientific Recommendation",
            abstract="Abstract",
            keywords=["transformer", "science", "recommendation"],
            topic_area=self.topic,
        )
        pdf = SimpleUploadedFile("paper.pdf", b"pdf", content_type="application/pdf")
        version = SubmissionVersion.objects.create(
            submission=self.submission,
            version_number=1,
            manuscript_pdf=pdf,
            supplementary_files_snapshot=[],
        )
        assignment = ReviewAssignment.objects.create(
            submission=self.submission,
            submission_version=version,
            reviewer=self.reviewer,
            invited_email=self.reviewer.email,
            status=STATUS_ACCEPTED,
        )
        review = Review.objects.create(
            assignment=assignment,
            summary="Strong paper",
            strengths="Clear methodology",
            weaknesses="Minor formatting",
            confidential_to_editor="",
            recommendation=RECOMMENDATION_ACCEPT,
        )
        self.certificate = ReviewerRecognitionCertificate.objects.create(
            review=review,
            submission=self.submission,
            author=self.author,
            reviewer=self.reviewer,
            article_title=self.submission.title,
            author_full_name=self.author.full_name,
            reviewer_full_name=self.reviewer.full_name,
        )

    def test_public_certificate_detail(self):
        response = self.client.get(f"{self.base}/certificates/public/{self.certificate.verification_code}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["submission_title"], self.submission.title)
        self.assertIn("certificate_page_url", response.data)
        self.assertIn("pdf_url", response.data)
        self.assertIn("qr_svg_url", response.data)

    def test_public_certificate_pdf_and_qr(self):
        pdf_response = self.client.get(f"{self.base}/certificates/public/{self.certificate.verification_code}/pdf/")
        self.assertEqual(pdf_response.status_code, status.HTTP_200_OK)
        self.assertEqual(pdf_response["Content-Type"], "application/pdf")
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))

        qr_response = self.client.get(f"{self.base}/certificates/public/{self.certificate.verification_code}/qr.svg")
        self.assertEqual(qr_response.status_code, status.HTTP_200_OK)
        self.assertEqual(qr_response["Content-Type"], "image/svg+xml")
        self.assertIn("<svg", qr_response.content.decode("utf-8"))

    def test_author_certificate_list_and_submission_payload(self):
        self.client.force_authenticate(user=self.author)
        my_response = self.client.get(f"{self.base}/certificates/my/")
        self.assertEqual(my_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(my_response.data), 1)
        self.assertEqual(my_response.data[0]["submission_id"], self.submission.id)

        submission_response = self.client.get(f"{self.base}/submissions/")
        self.assertEqual(submission_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(submission_response.data), 1)
        certs = submission_response.data[0]["certificates"]
        self.assertEqual(len(certs), 1)
        self.assertEqual(certs[0]["submission_id"], self.submission.id)

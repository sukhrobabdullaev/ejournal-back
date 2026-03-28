"""Tests for certificate API endpoints and submission payload integration."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import APPROVAL_APPROVED, User
from notifications.models import ReviewerRecognitionCertificate
from reviews.models import RECOMMENDATION_ACCEPT, Review, ReviewAssignment, STATUS_ACCEPTED
from submissions.models import Submission, SubmissionVersion, TopicArea


def make_user(roles, reviewer_status=None):
    role_str = "_".join(roles)
    user = User.objects.create_user(
        email=f"cert_{role_str}_{id(roles)}@test.com",
        password="testpass123",
        full_name=f"{role_str.title()} User",
        roles=roles,
    )
    if reviewer_status:
        user.reviewer_status = reviewer_status
        user.save(update_fields=["reviewer_status"])
    return user


class CertificateApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.author = make_user(["author"])
        self.reviewer = make_user(["reviewer"], reviewer_status=APPROVAL_APPROVED)
        self.topic = TopicArea.objects.create(name="AI", slug="ai-cert")
        self.submission = Submission.objects.create(
            author=self.author,
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
        response = self.client.get(f"/api/certificates/public/{self.certificate.verification_code}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["submission_title"], self.submission.title)
        self.assertIn("certificate_page_url", response.data)
        self.assertIn("pdf_url", response.data)
        self.assertIn("qr_svg_url", response.data)

    def test_public_certificate_pdf_and_qr(self):
        pdf_response = self.client.get(f"/api/certificates/public/{self.certificate.verification_code}/pdf/")
        self.assertEqual(pdf_response.status_code, status.HTTP_200_OK)
        self.assertEqual(pdf_response["Content-Type"], "application/pdf")
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))

        qr_response = self.client.get(f"/api/certificates/public/{self.certificate.verification_code}/qr.svg")
        self.assertEqual(qr_response.status_code, status.HTTP_200_OK)
        self.assertEqual(qr_response["Content-Type"], "image/svg+xml")
        self.assertIn("<svg", qr_response.content.decode("utf-8"))

    def test_author_certificate_list_and_submission_payload(self):
        self.client.force_authenticate(user=self.author)
        my_response = self.client.get("/api/certificates/my/")
        self.assertEqual(my_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(my_response.data), 1)
        self.assertEqual(my_response.data[0]["submission_id"], self.submission.id)

        submission_response = self.client.get("/api/submissions/")
        self.assertEqual(submission_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(submission_response.data), 1)
        certs = submission_response.data[0]["certificates"]
        self.assertEqual(len(certs), 1)
        self.assertEqual(certs[0]["submission_id"], self.submission.id)

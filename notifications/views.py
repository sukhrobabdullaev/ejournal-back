"""Certificate API views."""
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAuthor

from .certificate_utils import (
    build_frontend_certificate_url,
    build_frontend_journal_certificate_url,
)
from .certificates import (
    build_certificate_qr_svg,
    build_journal_publication_certificate_pdf,
    build_reviewer_recognition_pdf,
)
from .models import JournalPublicationCertificate, ReviewerRecognitionCertificate
from .serializers import (
    JournalPublicationCertificateSerializer,
    ReviewerRecognitionCertificateSerializer,
)


class MyCertificateListView(APIView):
    """List certificates for authenticated author."""

    permission_classes = [IsAuthenticated, IsAuthor]

    def get(self, request, *args, **kwargs):
        queryset = ReviewerRecognitionCertificate.objects.filter(
            author=request.user
        ).select_related("submission", "author", "reviewer")
        serializer = ReviewerRecognitionCertificateSerializer(
            queryset,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class MyJournalCertificateListView(APIView):
    """List journal publication certificates for authenticated author."""

    permission_classes = [IsAuthenticated, IsAuthor]

    def get(self, request, *args, **kwargs):
        queryset = JournalPublicationCertificate.objects.filter(
            author=request.user
        ).select_related("submission", "author", "issue")
        serializer = JournalPublicationCertificateSerializer(
            queryset,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicCertificateDetailView(APIView):
    """Public certificate details by verification code."""

    permission_classes = [AllowAny]

    def get(self, request, code, *args, **kwargs):
        certificate = (
            ReviewerRecognitionCertificate.objects.filter(verification_code=code)
            .select_related("submission", "author", "reviewer")
            .first()
        )
        if not certificate:
            return Response({"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ReviewerRecognitionCertificateSerializer(
            certificate,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicCertificatePdfView(APIView):
    """Public downloadable PDF certificate by verification code."""

    permission_classes = [AllowAny]

    def get(self, request, code, *args, **kwargs):
        certificate = (
            ReviewerRecognitionCertificate.objects.filter(verification_code=code)
            .select_related("submission", "author", "reviewer", "review")
            .first()
        )
        if not certificate:
            return Response({"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND)

        certificate_page_url = build_frontend_certificate_url(certificate.verification_code)
        review = getattr(certificate, "review", None)
        reviewer_comment_parts = []
        if review:
            if review.summary:
                reviewer_comment_parts.append(f"Summary: {review.summary}")
            if review.strengths:
                reviewer_comment_parts.append(f"Strengths: {review.strengths}")
            if review.weaknesses:
                reviewer_comment_parts.append(f"Weaknesses: {review.weaknesses}")
        reviewer_comment = "\n".join(reviewer_comment_parts).strip()
        editor_comment = (certificate.submission.decision_letter or "").strip()
        content = build_reviewer_recognition_pdf(
            submission_title=certificate.article_title,
            author_full_name=certificate.author_full_name,
            reviewer_full_name=certificate.reviewer_full_name,
            issued_at=certificate.issued_at,
            verification_url=certificate_page_url,
            reviewer_comment=reviewer_comment,
            editor_comment=editor_comment,
        )
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="reviewer-recognition-{certificate.verification_code}.pdf"'
        )
        return response


class PublicCertificateQrView(APIView):
    """Public QR SVG by certificate code."""

    permission_classes = [AllowAny]

    def get(self, request, code, *args, **kwargs):
        certificate = ReviewerRecognitionCertificate.objects.filter(
            verification_code=code
        ).first()
        if not certificate:
            return Response({"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND)

        certificate_page_url = build_frontend_certificate_url(certificate.verification_code)
        svg_content = build_certificate_qr_svg(certificate_page_url)
        return HttpResponse(svg_content, content_type="image/svg+xml")


class PublicJournalCertificateDetailView(APIView):
    """Public journal certificate details by verification code."""

    permission_classes = [AllowAny]

    def get(self, request, code, *args, **kwargs):
        certificate = (
            JournalPublicationCertificate.objects.filter(verification_code=code)
            .select_related("submission", "author", "issue")
            .first()
        )
        if not certificate:
            return Response({"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = JournalPublicationCertificateSerializer(
            certificate,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicJournalCertificatePdfView(APIView):
    """Public downloadable PDF for journal publication certificate."""

    permission_classes = [AllowAny]

    def get(self, request, code, *args, **kwargs):
        certificate = (
            JournalPublicationCertificate.objects.filter(verification_code=code)
            .select_related("submission", "author", "issue")
            .first()
        )
        if not certificate:
            return Response({"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND)

        content = build_journal_publication_certificate_pdf(
            author_full_name=certificate.author_full_name,
            article_title=certificate.article_title,
            issue_title=certificate.issue_title,
            volume=certificate.volume,
            issue_number=certificate.issue_number,
            publication_year=certificate.publication_year,
            publication_date=certificate.publication_date,
            author_affiliation=getattr(certificate.author, "affiliation", "") or "",
            author_country=getattr(certificate.author, "country", "") or "",
            certificate_code=str(certificate.verification_code),
        )
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="journal-certificate-{certificate.verification_code}.pdf"'
        )
        return response


class PublicJournalCertificateQrView(APIView):
    """Public QR SVG by journal certificate code."""

    permission_classes = [AllowAny]

    def get(self, request, code, *args, **kwargs):
        certificate = JournalPublicationCertificate.objects.filter(
            verification_code=code
        ).first()
        if not certificate:
            return Response({"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND)

        certificate_page_url = build_frontend_journal_certificate_url(certificate.verification_code)
        svg_content = build_certificate_qr_svg(certificate_page_url)
        return HttpResponse(svg_content, content_type="image/svg+xml")

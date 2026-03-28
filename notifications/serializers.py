"""Serializers for certificate payloads."""
from rest_framework import serializers

from .certificate_utils import (
    build_absolute_url,
    build_certificate_pdf_api_path,
    build_certificate_public_api_path,
    build_certificate_qr_api_path,
    build_frontend_certificate_url,
    build_frontend_journal_certificate_url,
    build_journal_certificate_pdf_api_path,
    build_journal_certificate_public_api_path,
    build_journal_certificate_qr_api_path,
)
from .models import JournalPublicationCertificate, ReviewerRecognitionCertificate


class ReviewerRecognitionCertificateSerializer(serializers.ModelSerializer):
    """Certificate serializer for author dashboard and public certificate view."""

    submission_id = serializers.IntegerField(source="submission.id", read_only=True)
    submission_title = serializers.CharField(source="article_title", read_only=True)
    reviewer_name = serializers.CharField(source="reviewer_full_name", read_only=True)
    author_name = serializers.CharField(source="author_full_name", read_only=True)
    certificate_page_url = serializers.SerializerMethodField()
    public_api_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    qr_svg_url = serializers.SerializerMethodField()

    class Meta:
        model = ReviewerRecognitionCertificate
        fields = [
            "id",
            "submission_id",
            "submission_title",
            "author_name",
            "reviewer_name",
            "issued_at",
            "verification_code",
            "certificate_page_url",
            "public_api_url",
            "pdf_url",
            "qr_svg_url",
        ]

    def get_certificate_page_url(self, obj):
        return build_frontend_certificate_url(obj.verification_code)

    def get_public_api_url(self, obj):
        request = self.context.get("request")
        return build_absolute_url(request, build_certificate_public_api_path(obj.verification_code))

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        return build_absolute_url(request, build_certificate_pdf_api_path(obj.verification_code))

    def get_qr_svg_url(self, obj):
        request = self.context.get("request")
        return build_absolute_url(request, build_certificate_qr_api_path(obj.verification_code))


class JournalPublicationCertificateSerializer(serializers.ModelSerializer):
    """Journal publication certificate serializer for author dashboard/public view."""

    submission_id = serializers.IntegerField(source="submission.id", read_only=True)
    submission_title = serializers.CharField(source="article_title", read_only=True)
    author_name = serializers.CharField(source="author_full_name", read_only=True)
    certificate_page_url = serializers.SerializerMethodField()
    public_api_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    qr_svg_url = serializers.SerializerMethodField()

    class Meta:
        model = JournalPublicationCertificate
        fields = [
            "id",
            "submission_id",
            "submission_title",
            "author_name",
            "issue_title",
            "volume",
            "issue_number",
            "publication_year",
            "publication_date",
            "issued_at",
            "verification_code",
            "certificate_page_url",
            "public_api_url",
            "pdf_url",
            "qr_svg_url",
        ]

    def get_certificate_page_url(self, obj):
        return build_frontend_journal_certificate_url(obj.verification_code)

    def get_public_api_url(self, obj):
        request = self.context.get("request")
        return build_absolute_url(
            request,
            build_journal_certificate_public_api_path(obj.verification_code),
        )

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        return build_absolute_url(
            request,
            build_journal_certificate_pdf_api_path(obj.verification_code),
        )

    def get_qr_svg_url(self, obj):
        request = self.context.get("request")
        return build_absolute_url(
            request,
            build_journal_certificate_qr_api_path(obj.verification_code),
        )

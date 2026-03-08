"""Submission serializers."""
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Submission,
    SubmissionSupplementaryFile,
    SubmissionVersion,
    TopicArea,
    STATUS_DESK_REJECTED,
    STATUS_REJECTED,
)


class TopicAreaSerializer(serializers.ModelSerializer):
    """Serializer for topic area."""

    class Meta:
        model = TopicArea
        fields = ["id", "name", "slug"]


class SubmissionSupplementaryFileSerializer(serializers.ModelSerializer):
    """Serializer for supplementary file."""

    class Meta:
        model = SubmissionSupplementaryFile
        fields = ["id", "file", "name", "created_at"]
        read_only_fields = ["created_at"]


class SubmissionSerializer(serializers.ModelSerializer):
    """Serializer for submission (author view)."""

    supplementary_files = SubmissionSupplementaryFileSerializer(many=True, read_only=True)
    topic_area = TopicAreaSerializer(read_only=True)
    reason = serializers.SerializerMethodField()
    topic_area_id = serializers.PrimaryKeyRelatedField(
        queryset=TopicArea.objects.all(),
        source="topic_area",
        write_only=True,
        required=False,
        allow_null=True,
    )
    manuscript_pdf = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id",
            "status",
            "reason",
            "title",
            "abstract",
            "keywords",
            "topic_area",
            "topic_area_id",
            "originality_confirmation",
            "plagiarism_agreement",
            "ethics_compliance",
            "copyright_agreement",
            "manuscript_pdf",
            "supplementary_files",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "reason", "supplementary_files", "created_at", "updated_at"]

    def get_manuscript_pdf(self, obj):
        """Return manuscript URL or None (avoids ValueError on empty FileField)."""
        f = obj.manuscript_pdf
        if not f:
            return None
        try:
            url = f.url
        except (ValueError, AttributeError):
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    def get_reason(self, obj):
        if obj.status == STATUS_DESK_REJECTED:
            return obj.desk_reject_reason or ""
        if obj.status == STATUS_REJECTED:
            return obj.decision_letter or ""
        return ""

    def validate_keywords(self, value):
        """Ensure keywords is a list of 0-10 strings (3+ required on submit)."""
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Keywords must be a list.")
        kw = [str(k).strip() for k in value if k]
        if len(kw) > 10:
            raise serializers.ValidationError("At most 10 keywords allowed.")
        return kw

    def create(self, validated_data):
        """Create submission; set agreement timestamps when True."""
        now = timezone.now()
        for field, ts_field in [
            ("originality_confirmation", "originality_confirmed_at"),
            ("plagiarism_agreement", "plagiarism_agreed_at"),
            ("ethics_compliance", "ethics_confirmed_at"),
            ("copyright_agreement", "copyright_agreed_at"),
        ]:
            if validated_data.get(field):
                validated_data[ts_field] = now
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Set acceptance timestamps when agreements are set to True."""
        now = timezone.now()
        for field, ts_field in [
            ("originality_confirmation", "originality_confirmed_at"),
            ("plagiarism_agreement", "plagiarism_agreed_at"),
            ("ethics_compliance", "ethics_confirmed_at"),
            ("copyright_agreement", "copyright_agreed_at"),
        ]:
            if validated_data.get(field) and not getattr(instance, ts_field):
                setattr(instance, ts_field, now)
        return super().update(instance, validated_data)


class SubmissionCreateSerializer(serializers.ModelSerializer):
    """Minimal serializer for creating a draft."""

    class Meta:
        model = Submission
        fields = []



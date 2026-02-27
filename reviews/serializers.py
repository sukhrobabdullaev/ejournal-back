"""Review serializers."""
from rest_framework import serializers

from .models import (
    RECOMMENDATION_CHOICES,
    Review,
    ReviewAssignment,
)


class SubmissionVersionMinimalSerializer(serializers.Serializer):
    """Minimal submission version info for reviewer."""

    id = serializers.IntegerField()
    version_number = serializers.IntegerField()


class ReviewAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for review assignment (reviewer view)."""

    submission_title = serializers.CharField(source="submission.title", read_only=True)
    submission_abstract = serializers.CharField(source="submission.abstract", read_only=True)
    submission_version = SubmissionVersionMinimalSerializer(read_only=True)
    manuscript_url = serializers.SerializerMethodField()

    class Meta:
        model = ReviewAssignment
        fields = [
            "id",
            "submission",
            "submission_title",
            "submission_abstract",
            "submission_version",
            "manuscript_url",
            "status",
            "due_date",
            "invited_at",
            "responded_at",
        ]
        read_only_fields = fields

    def get_manuscript_url(self, obj):
        """URL to access manuscript (from submission_version)."""
        version = obj.submission_version
        if version and version.manuscript_pdf:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(version.manuscript_pdf.url)
            return version.manuscript_pdf.url
        return None


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for submitting a review."""

    class Meta:
        model = Review
        fields = [
            "summary",
            "strengths",
            "weaknesses",
            "confidential_to_editor",
            "recommendation",
        ]

    def validate_recommendation(self, value):
        if value not in dict(RECOMMENDATION_CHOICES):
            raise serializers.ValidationError("Invalid recommendation.")
        return value

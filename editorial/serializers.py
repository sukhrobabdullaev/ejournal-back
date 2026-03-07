"""Editorial serializers."""
from django.db.models import ObjectDoesNotExist
from rest_framework import serializers

from accounts.models import User
from reviews.models import ReviewAssignment
from submissions.models import Submission
from submissions.serializers import SubmissionSupplementaryFileSerializer, TopicAreaSerializer


class EditorialSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for editorial submission list/detail."""

    topic_area = TopicAreaSerializer(read_only=True)
    supplementary_files = SubmissionSupplementaryFileSerializer(many=True, read_only=True)
    review_assignments = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id",
            "status",
            "title",
            "abstract",
            "keywords",
            "topic_area",
            "author",
            "desk_reject_reason",
            "editorial_decision",
            "decision_letter",
            "manuscript_pdf",
            "supplementary_files",
            "created_at",
            "updated_at",
            "review_assignments",
        ]

    def get_review_assignments(self, obj):
        result = []
        for a in obj.review_assignments.all():
            item = {
                "id": a.id,
                "reviewer": a.reviewer_id,
                "reviewer_email": a.reviewer.email if a.reviewer else a.invited_email,
                "status": a.status,
                "due_date": a.due_date,
                "invited_at": a.invited_at,
            }
            try:
                r = a.review
                item["review"] = {
                    "summary": r.summary,
                    "strengths": r.strengths,
                    "weaknesses": r.weaknesses,
                    "confidential_to_editor": r.confidential_to_editor,
                    "recommendation": r.recommendation,
                    "submitted_at": r.submitted_at,
                }
            except ObjectDoesNotExist:
                item["review"] = None
            result.append(item)
        return result


class DeskRejectSerializer(serializers.Serializer):
    """Serializer for desk reject action."""

    reason = serializers.CharField(required=True, allow_blank=False)


class InviteReviewerSerializer(serializers.Serializer):
    """Serializer for invite reviewer action."""

    reviewer_user_id = serializers.IntegerField(required=False, allow_null=True)
    reviewer_email = serializers.EmailField(required=False, allow_blank=True)
    due_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        user_id = attrs.get("reviewer_user_id")
        email = attrs.get("reviewer_email", "").strip()
        if user_id and email:
            raise serializers.ValidationError("Provide either reviewer_user_id or reviewer_email, not both.")
        if not user_id and not email:
            raise serializers.ValidationError("Provide reviewer_user_id or reviewer_email.")
        return attrs


class DecisionSerializer(serializers.Serializer):
    """Serializer for editorial decision."""

    decision = serializers.ChoiceField(
        choices=["accept", "reject", "revision_required"],
        required=True,
    )
    decision_letter = serializers.CharField(required=True, allow_blank=False)


class ReviewerOptionSerializer(serializers.ModelSerializer):
    """Lightweight serializer for reviewer dropdown options."""

    is_approved_reviewer = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "affiliation",
            "country",
            "is_approved_reviewer",
        ]

    def get_is_approved_reviewer(self, obj):
        return obj.is_approved_reviewer()

"""Editorial serializers."""
from rest_framework import serializers

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
        return [
            {
                "id": a.id,
                "reviewer": a.reviewer_id,
                "reviewer_email": a.reviewer.email if a.reviewer else a.invited_email,
                "status": a.status,
                "due_date": a.due_date,
                "invited_at": a.invited_at,
            }
            for a in obj.review_assignments.select_related("reviewer").all()
        ]


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

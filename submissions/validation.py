"""Submission validation helpers."""
from rest_framework import serializers

from .models import STATUS_REVISION_REQUIRED, STATUS_SUBMITTED


def validate_submission_ready_for_submit(submission):
    """Validate submission has all required data for submit. Raises ValidationError if not."""
    if submission.status not in (STATUS_SUBMITTED, STATUS_REVISION_REQUIRED):
        raise serializers.ValidationError(
            "Submission can only be finalized from submitted or revision_required status."
        )

    if not all([
        submission.originality_confirmation,
        submission.plagiarism_agreement,
        submission.ethics_compliance,
        submission.copyright_agreement,
    ]):
        raise serializers.ValidationError("All agreements must be confirmed.")

    if not submission.title or not submission.title.strip():
        raise serializers.ValidationError("Title is required.")
    if not submission.abstract or not submission.abstract.strip():
        raise serializers.ValidationError("Abstract is required.")

    keywords = submission.keywords or []
    if len(keywords) < 3:
        raise serializers.ValidationError("At least 3 keywords required.")

    if not submission.topic_area_id:
        raise serializers.ValidationError("Topic area is required.")

    if not submission.manuscript_pdf:
        raise serializers.ValidationError("Manuscript PDF is required.")

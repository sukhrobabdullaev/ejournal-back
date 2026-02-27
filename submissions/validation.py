"""Submission validation helpers."""
from rest_framework import serializers

from .models import STATUS_DRAFT


def validate_submission_ready_for_submit(submission):
    """Validate submission has all required data for submit. Raises ValidationError if not."""
    if submission.status != STATUS_DRAFT:
        raise serializers.ValidationError("Only drafts can be submitted.")

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

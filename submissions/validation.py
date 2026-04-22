"""Submission validation helpers."""
import re
from urllib.parse import urlparse

from rest_framework import serializers

from .models import STATUS_REVISION_REQUIRED, STATUS_SUBMITTED


ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", re.IGNORECASE)


def _is_valid_google_scholar_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    return (
        parsed.scheme in {"http", "https"}
        and "scholar.google." in host
        and "/citations" in path
    )


def _validate_author_profile_requirements(submission):
    author = submission.author
    if not author or not author.has_role("author"):
        return

    orcid_id = (author.orcid_id or "").strip()
    scholar_url = (author.google_scholar_url or "").strip()

    missing_items = []
    if not orcid_id:
        missing_items.append("ORCID iD")
    if not scholar_url:
        missing_items.append("Google Scholar URL")

    if missing_items:
        raise serializers.ValidationError(
            "Author profile is incomplete. Please add "
            + " and ".join(missing_items)
            + " before submitting the manuscript."
        )

    if not ORCID_PATTERN.match(orcid_id):
        raise serializers.ValidationError(
            "Author ORCID iD format is invalid. Use 0000-0000-0000-0000."
        )

    if not _is_valid_google_scholar_url(scholar_url):
        raise serializers.ValidationError(
            "Author Google Scholar URL is invalid. Use a /citations profile URL."
        )


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

    _validate_author_profile_requirements(submission)

    if not submission.manuscript_pdf:
        raise serializers.ValidationError("Manuscript PDF is required.")

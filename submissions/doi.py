"""Local DOI helpers for submission publishing workflow."""
from __future__ import annotations

from django.conf import settings

from .models import DOI_STATUS_PENDING, Submission

DEFAULT_DOI_PREFIX = "10.5555"


def get_doi_prefix() -> str:
    """Return configured DOI prefix with a safe default for local usage."""
    prefix = str(getattr(settings, "DOI_PREFIX", DEFAULT_DOI_PREFIX) or "").strip()
    return prefix or DEFAULT_DOI_PREFIX


def build_local_doi(submission: Submission) -> str:
    """Build a deterministic local DOI for a submission."""
    volume = submission.issue.volume if submission.issue else 0
    issue_number = submission.issue.issue_number if submission.issue else 0
    return f"{get_doi_prefix()}/ejournal.v{volume}.i{issue_number}.a{submission.id}"


def ensure_local_doi(submission: Submission, save: bool = True) -> str:
    """Assign a local DOI once and keep it stable across subsequent updates."""
    if submission.doi:
        return submission.doi

    if not submission.id:
        raise ValueError("Submission must be saved before DOI can be generated.")

    submission.doi = build_local_doi(submission)
    submission.doi_status = submission.doi_status or DOI_STATUS_PENDING

    if save:
        submission.save(update_fields=["doi", "doi_status", "updated_at"])

    return submission.doi

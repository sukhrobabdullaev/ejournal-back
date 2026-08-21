"""Utility helpers for certificate links."""
from django.conf import settings
from django.urls import reverse


def build_frontend_certificate_url(code) -> str:
    """Build frontend certificate page URL for sharing and QR scan destination."""
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/certificate/{code}"


def build_frontend_journal_certificate_url(code) -> str:
    """Build frontend journal certificate page URL for sharing and QR destination."""
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/journal-certificate/{code}"


def build_frontend_dashboard_url() -> str:
    """Build frontend dashboard URL used in notification emails."""
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/dashboard"


def build_frontend_editor_dashboard_url() -> str:
    """Build frontend editor dashboard URL used in notification emails."""
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/editor"


def build_frontend_submission_url(submission_id) -> str:
    """Build frontend submission detail URL for authors."""
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/submission/{submission_id}"


def build_frontend_editor_submission_url(submission_id) -> str:
    """Build frontend editor submission detail URL."""
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/editor/submissions/{submission_id}"


def build_frontend_review_invite_url(token) -> str:
    """Build frontend reviewer invitation URL."""
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/review/invite/{token}"


def build_certificate_public_api_path(code, journal_slug) -> str:
    return reverse("certificate-public-detail", kwargs={"journal_slug": journal_slug, "code": str(code)})


def build_certificate_pdf_api_path(code, journal_slug) -> str:
    return reverse("certificate-public-pdf", kwargs={"journal_slug": journal_slug, "code": str(code)})


def build_certificate_qr_api_path(code, journal_slug) -> str:
    return reverse("certificate-public-qr", kwargs={"journal_slug": journal_slug, "code": str(code)})


def build_journal_certificate_public_api_path(code, journal_slug) -> str:
    return reverse("journal-certificate-public-detail", kwargs={"journal_slug": journal_slug, "code": str(code)})


def build_journal_certificate_pdf_api_path(code, journal_slug) -> str:
    return reverse("journal-certificate-public-pdf", kwargs={"journal_slug": journal_slug, "code": str(code)})


def build_journal_certificate_qr_api_path(code, journal_slug) -> str:
    return reverse("journal-certificate-public-qr", kwargs={"journal_slug": journal_slug, "code": str(code)})


def build_absolute_url(request, path: str) -> str:
    if request is None:
        return path
    return request.build_absolute_uri(path)

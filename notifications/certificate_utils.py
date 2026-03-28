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


def build_certificate_public_api_path(code) -> str:
    return reverse("certificate-public-detail", kwargs={"code": str(code)})


def build_certificate_pdf_api_path(code) -> str:
    return reverse("certificate-public-pdf", kwargs={"code": str(code)})


def build_certificate_qr_api_path(code) -> str:
    return reverse("certificate-public-qr", kwargs={"code": str(code)})


def build_journal_certificate_public_api_path(code) -> str:
    return reverse("journal-certificate-public-detail", kwargs={"code": str(code)})


def build_journal_certificate_pdf_api_path(code) -> str:
    return reverse("journal-certificate-public-pdf", kwargs={"code": str(code)})


def build_journal_certificate_qr_api_path(code) -> str:
    return reverse("journal-certificate-public-qr", kwargs={"code": str(code)})


def build_absolute_url(request, path: str) -> str:
    if request is None:
        return path
    return request.build_absolute_uri(path)

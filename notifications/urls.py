"""Notification/certificate API URL routes."""
from django.urls import path

from .views import (
    MyJournalCertificateListView,
    MyCertificateListView,
    PublicJournalCertificateDetailView,
    PublicJournalCertificatePdfView,
    PublicJournalCertificateQrView,
    PublicCertificateDetailView,
    PublicCertificatePdfView,
    PublicCertificateQrView,
    ContactFormView,
)

urlpatterns = [
    path("contact/", ContactFormView.as_view(), name="contact-form"),
    path("my/", MyCertificateListView.as_view(), name="certificate-my-list"),
    path("journal/my/", MyJournalCertificateListView.as_view(), name="journal-certificate-my-list"),
    path("public/<uuid:code>/", PublicCertificateDetailView.as_view(), name="certificate-public-detail"),
    path("public/<uuid:code>/pdf/", PublicCertificatePdfView.as_view(), name="certificate-public-pdf"),
    path("public/<uuid:code>/qr.svg", PublicCertificateQrView.as_view(), name="certificate-public-qr"),
    path(
        "journal/public/<uuid:code>/",
        PublicJournalCertificateDetailView.as_view(),
        name="journal-certificate-public-detail",
    ),
    path(
        "journal/public/<uuid:code>/pdf/",
        PublicJournalCertificatePdfView.as_view(),
        name="journal-certificate-public-pdf",
    ),
    path(
        "journal/public/<uuid:code>/qr.svg",
        PublicJournalCertificateQrView.as_view(),
        name="journal-certificate-public-qr",
    ),
]

"""Notification admin."""
from django.contrib import admin
from .models import (
    EmailLog,
    JournalPublicationCertificate,
    Notification,
    ReviewerRecognitionCertificate,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "event_type", "user", "status", "idempotency_key", "sent_at"]
    list_filter = ["event_type", "status"]


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ["id", "to_email", "subject", "status", "created_at"]
    list_filter = ["status"]


@admin.register(ReviewerRecognitionCertificate)
class ReviewerRecognitionCertificateAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "submission",
        "author_full_name",
        "reviewer_full_name",
        "issued_at",
    ]
    search_fields = ["article_title", "author_full_name", "reviewer_full_name"]
    list_filter = ["issued_at"]


@admin.register(JournalPublicationCertificate)
class JournalPublicationCertificateAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "issue",
        "submission",
        "author_full_name",
        "publication_year",
        "issued_at",
        "email_sent_at",
    ]
    search_fields = ["article_title", "author_full_name", "issue_title"]
    list_filter = ["publication_year", "issued_at", "email_sent_at"]

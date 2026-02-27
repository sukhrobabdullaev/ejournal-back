"""Notification admin."""
from django.contrib import admin
from .models import EmailLog, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "event_type", "user", "status", "idempotency_key", "sent_at"]
    list_filter = ["event_type", "status"]


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ["id", "to_email", "subject", "status", "created_at"]
    list_filter = ["status"]

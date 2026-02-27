"""Notifications app configuration."""
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Notifications app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"
    verbose_name = "Notifications"

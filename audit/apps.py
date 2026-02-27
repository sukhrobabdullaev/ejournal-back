"""Audit app configuration."""
from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Audit app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"
    verbose_name = "Audit"

"""Journals app configuration."""
from django.apps import AppConfig


class JournalsConfig(AppConfig):
    """Journals (tenant) app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "journals"
    verbose_name = "Journals"

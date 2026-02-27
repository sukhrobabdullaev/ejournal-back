"""Submissions app configuration."""
from django.apps import AppConfig


class SubmissionsConfig(AppConfig):
    """Submissions app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "submissions"
    verbose_name = "Submissions"

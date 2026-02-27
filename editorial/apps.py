"""Editorial app configuration."""
from django.apps import AppConfig


class EditorialConfig(AppConfig):
    """Editorial app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "editorial"
    verbose_name = "Editorial"

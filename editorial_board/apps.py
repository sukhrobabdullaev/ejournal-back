"""Editorial board app configuration."""
from django.apps import AppConfig


class EditorialBoardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "editorial_board"
    verbose_name = "Editorial Board"

"""Editorial board models."""
from django.db import models


ROLE_EDITOR_IN_CHIEF = "editor_in_chief"
ROLE_MANAGING_EDITOR = "managing_editor"
ROLE_ASSOCIATE_EDITOR = "associate_editor"

ROLE_CHOICES = [
    (ROLE_EDITOR_IN_CHIEF, "Editor-in-Chief"),
    (ROLE_MANAGING_EDITOR, "Managing Editor"),
    (ROLE_ASSOCIATE_EDITOR, "Associate Editor"),
]


class EditorialBoardMember(models.Model):
    """Board member profile for public editorial board page."""

    journal = models.ForeignKey(
        "journals.Journal",
        on_delete=models.CASCADE,
        related_name="board_members",
    )
    name = models.CharField(max_length=255)
    affiliation = models.CharField(max_length=255, blank=True)
    expertise = models.JSONField(default=list, help_text="List of expertise tags")
    email = models.EmailField(blank=True)
    linkedin_url = models.URLField(blank=True)
    profile_image = models.ImageField(upload_to="editorial_board/", blank=True, null=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, db_index=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order within role")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "editorial_board_member"
        ordering = ["role", "order", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

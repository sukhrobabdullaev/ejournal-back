"""Account models."""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager

ROLE_AUTHOR = "author"
ROLE_REVIEWER = "reviewer"
ROLE_EDITOR = "editor"
ROLE_CHOICES = [ROLE_AUTHOR, ROLE_REVIEWER, ROLE_EDITOR]

APPROVAL_PENDING = "pending"
APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"
APPROVAL_STATUS_CHOICES = [
    (APPROVAL_PENDING, "Pending"),
    (APPROVAL_APPROVED, "Approved"),
    (APPROVAL_REJECTED, "Rejected"),
]


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with email as login and role-based approval."""

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)

    affiliation = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)
    orcid_id = models.CharField(max_length=50, blank=True)
    is_email_verified = models.BooleanField(default=False)

    roles = models.JSONField(default=list)  # ["author", "reviewer", "editor"]
    reviewer_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        null=True,
        blank=True,
    )
    editor_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        null=True,
        blank=True,
    )
    why_to_be = models.TextField(blank=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return self.email

    def has_role(self, role):
        """Check if user has a given role."""
        return role in (self.roles or [])

    def is_approved_reviewer(self):
        """Reviewer role + approved status."""
        return self.has_role(ROLE_REVIEWER) and self.reviewer_status == APPROVAL_APPROVED

    def is_approved_editor(self):
        """Editor role + approved status."""
        return self.has_role(ROLE_EDITOR) and self.editor_status == APPROVAL_APPROVED

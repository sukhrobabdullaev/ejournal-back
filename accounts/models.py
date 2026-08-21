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
    google_scholar_url = models.URLField(max_length=500, blank=True)
    is_email_verified = models.BooleanField(default=False)

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

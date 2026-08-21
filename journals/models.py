"""Journal (tenant) models."""
from django.conf import settings
from django.db import models

MEMBERSHIP_ROLE_AUTHOR = "author"
MEMBERSHIP_ROLE_REVIEWER = "reviewer"
MEMBERSHIP_ROLE_EDITOR = "editor"
MEMBERSHIP_ROLE_CHOICES = [
    (MEMBERSHIP_ROLE_AUTHOR, "Author"),
    (MEMBERSHIP_ROLE_REVIEWER, "Reviewer"),
    (MEMBERSHIP_ROLE_EDITOR, "Editor"),
]

MEMBERSHIP_STATUS_PENDING = "pending"
MEMBERSHIP_STATUS_APPROVED = "approved"
MEMBERSHIP_STATUS_REJECTED = "rejected"
MEMBERSHIP_STATUS_CHOICES = [
    (MEMBERSHIP_STATUS_PENDING, "Pending"),
    (MEMBERSHIP_STATUS_APPROVED, "Approved"),
    (MEMBERSHIP_STATUS_REJECTED, "Rejected"),
]


class Journal(models.Model):
    """A single university/publisher's journal tenant."""

    slug = models.SlugField(unique=True, max_length=60)
    name = models.CharField(max_length=255)
    tagline = models.CharField(max_length=500, blank=True)
    logo = models.ImageField(upload_to="journals/logos/", blank=True, null=True)
    accent_color = models.CharField(
        max_length=7,
        default="#2563eb",
        help_text="Hex color, e.g. #2563eb. Maps to --color-accent-blue.",
    )
    doi_prefix = models.CharField(max_length=32, default="10.5555")
    contact_email = models.EmailField(blank=True)
    from_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Display name used as email sender / sign-off. Falls back to `name` if blank.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "journals_journal"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def effective_from_name(self) -> str:
        return self.from_name or self.name


class JournalMembership(models.Model):
    """A user's role and approval status within one specific journal.

    Author role has no approval gate (mirrors the pre-existing global
    IsAuthor behavior, which never checked a status field) - status is
    only meaningful for reviewer/editor rows. Author rows are created
    with status='approved' and it is simply ignored by permission checks.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="journal_memberships",
    )
    journal = models.ForeignKey(
        Journal,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=MEMBERSHIP_ROLE_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_STATUS_CHOICES,
        default=MEMBERSHIP_STATUS_PENDING,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    why_to_be = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "journals_journal_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "journal", "role"], name="uniq_membership_user_journal_role"
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.role} @ {self.journal.slug} ({self.status})"

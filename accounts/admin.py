"""Account admin."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for custom User model."""

    list_display = ["email", "full_name", "roles", "reviewer_status", "editor_status", "is_active"]
    list_filter = ["is_staff", "is_active", "reviewer_status", "editor_status"]
    search_fields = ["email", "full_name"]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "affiliation", "country", "orcid_id", "is_email_verified")}),
        ("Roles", {"fields": ("roles", "reviewer_status", "editor_status", "why_to_be")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password1", "password2"),
            },
        ),
    )

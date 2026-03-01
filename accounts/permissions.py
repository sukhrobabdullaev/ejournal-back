"""Custom permission classes for role-based access."""
from rest_framework import permissions

from .models import ROLE_AUTHOR, ROLE_EDITOR, ROLE_REVIEWER


class IsEmailVerified(permissions.BasePermission):
    """User must have verified email. Staff users are exempt."""

    message = "Email verification required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return request.user.is_email_verified


class IsAuthor(permissions.BasePermission):
    """User must have active author role and verified email."""

    message = "Author role required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not request.user.is_staff and not request.user.is_email_verified:
            self.message = "Email verification required."
            return False
        if not request.user.has_role(ROLE_AUTHOR):
            self.message = "Author role required."
            return False
        return True


class IsApprovedReviewer(permissions.BasePermission):
    """User must have reviewer role + approved status + verified email."""

    message = "Approved reviewer role required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not request.user.is_staff and not request.user.is_email_verified:
            self.message = "Email verification required."
            return False
        if not request.user.is_approved_reviewer():
            self.message = "Approved reviewer role required."
            return False
        return True


class IsApprovedEditor(permissions.BasePermission):
    """User must have editor role + approved status + verified email."""

    message = "Approved editor role required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not request.user.is_staff and not request.user.is_email_verified:
            self.message = "Email verification required."
            return False
        if not request.user.is_approved_editor():
            self.message = "Approved editor role required."
            return False
        return True

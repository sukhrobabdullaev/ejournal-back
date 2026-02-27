"""Custom permission classes for role-based access."""
from rest_framework import permissions

from .models import ROLE_AUTHOR, ROLE_EDITOR, ROLE_REVIEWER


class IsAuthor(permissions.BasePermission):
    """User must have active author role."""

    message = "Author role required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.has_role(ROLE_AUTHOR)


class IsApprovedReviewer(permissions.BasePermission):
    """User must have reviewer role + approved status."""

    message = "Approved reviewer role required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_approved_reviewer()


class IsApprovedEditor(permissions.BasePermission):
    """User must have editor role + approved status."""

    message = "Approved editor role required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_approved_editor()

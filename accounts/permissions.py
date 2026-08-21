from rest_framework import permissions

from journals import services as journal_services


def _get_request_user(request):
    """Safely return request user, or None when missing."""
    user = getattr(request, 'user', None)
    if user is not None:
        return user
    return getattr(request, '_force_auth_user', None)


def _call_or_value(value):
    """Support both bool attributes and bool-returning methods."""
    return value() if callable(value) else value

class IsEmailVerified(permissions.BasePermission):
    message = "Your email address must be verified to perform this action."

    def has_permission(self, request, view):
        user = _get_request_user(request)
        if not user or not user.is_authenticated:
            return False

        return getattr(user, 'is_email_verified', False) is True

class IsApprovedEditor(permissions.BasePermission):
    message = "Your Editor role has not been approved yet, or you don't have this role."

    def has_permission(self, request, view):
        user = _get_request_user(request)
        if not user or not user.is_authenticated:
            return False
        if not getattr(user, 'is_email_verified', False):
            return False

        journal = getattr(request, 'journal', None)
        return journal_services.is_approved_editor(user, journal)

class IsApprovedReviewer(permissions.BasePermission):
    message = "Your Reviewer role has not been approved, or you don't have this role."

    def has_permission(self, request, view):
        user = _get_request_user(request)
        if not user or not user.is_authenticated:
            return False
        if not getattr(user, 'is_email_verified', False):
            return False

        journal = getattr(request, 'journal', None)
        return journal_services.is_approved_reviewer(user, journal)

class IsAuthor(permissions.BasePermission):
    message = "You don't have the Author role."

    def has_permission(self, request, view):
        user = _get_request_user(request)
        if not user or not user.is_authenticated:
            return False
        if not getattr(user, 'is_email_verified', False):
            return False

        journal = getattr(request, 'journal', None)
        return journal_services.is_author(user, journal)

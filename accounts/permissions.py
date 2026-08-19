from rest_framework import permissions


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
            
        roles = getattr(user, 'roles', []) or []
        has_role = 'editor' in roles
        is_approved = (
            getattr(user, 'editor_status', None) == 'approved'
            or bool(_call_or_value(getattr(user, 'is_approved_editor', False)))
        )
        
        return bool(has_role and is_approved)

class IsApprovedReviewer(permissions.BasePermission):
    message = "Your Reviewer role has not been approved, or you don't have this role."

    def has_permission(self, request, view):
        user = _get_request_user(request)
        if not user or not user.is_authenticated:
            return False
        if not getattr(user, 'is_email_verified', False):
            return False
            
        roles = getattr(user, 'roles', []) or []
        has_role = 'reviewer' in roles
        is_approved = (
            getattr(user, 'reviewer_status', None) == 'approved'
            or bool(_call_or_value(getattr(user, 'is_approved_reviewer', False)))
        )
        
        return bool(has_role and is_approved)

class IsAuthor(permissions.BasePermission):
    message = "You don't have the Author role."

    def has_permission(self, request, view):
        user = _get_request_user(request)
        if not user or not user.is_authenticated:
            return False
        if not getattr(user, 'is_email_verified', False):
            return False
            
        roles = getattr(user, 'roles', []) or []
        has_role = 'author' in roles
        
        return bool(has_role)
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
    message = "Ushbu amalni bajarish uchun elektron pochtangiz tasdiqlangan bo'lishi shart."

    def has_permission(self, request, view):
        user = _get_request_user(request)
        if not user or not user.is_authenticated:
            return False
            
        return getattr(user, 'is_email_verified', False) is True

class IsApprovedEditor(permissions.BasePermission):
    message = "Sizning Editor rolingiz hali tasdiqlanmagan yoki sizda bu rol yo'q."

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
    message = "Sizning Taqrizchi rolingiz tasdiqlanmagan yoki sizda bu rol yo'q."

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
    message = "Sizda Muallif (Author) roli yo'q."

    def has_permission(self, request, view):
        user = _get_request_user(request)
        if not user or not user.is_authenticated:
            return False
        if not getattr(user, 'is_email_verified', False):
            return False
            
        roles = getattr(user, 'roles', []) or []
        has_role = 'author' in roles
        
        return bool(has_role)
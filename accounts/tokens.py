"""Email verification token helpers."""
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

from .models import User


signer = TimestampSigner()


def generate_email_verification_token(user: User) -> str:
    """Return a signed token for email verification."""
    value = f"{user.id}:{user.email}"
    return signer.sign(value)


def verify_email_verification_token(token: str, max_age_seconds: int = 60 * 60 * 24 * 3) -> User | None:
    """
    Verify token and return user or None.
    max_age_seconds defaults to 3 days.
    """
    try:
        value = signer.unsign(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None

    try:
        user_id_str, email = value.split(":", 1)
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        return None

    try:
        return User.objects.get(id=user_id, email=email)
    except User.DoesNotExist:
        return None


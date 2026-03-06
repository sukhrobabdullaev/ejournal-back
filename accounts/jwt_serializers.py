"""Custom JWT serializers with user_id and roles in token payload."""
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Add user_id and roles to JWT payload and enforce email verification."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["user_id"] = user.id
        token["email"] = user.email
        token["roles"] = user.roles or []
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user
        if not getattr(user, "is_email_verified", False):
            raise AuthenticationFailed(
                detail="Email not verified. Please verify your email before logging in.",
                code="email_not_verified",
            )

        return data

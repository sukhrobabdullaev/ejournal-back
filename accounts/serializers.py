"""Account serializers."""
from rest_framework import serializers

from .models import (
    ROLE_CHOICES,
    APPROVAL_PENDING,
    ROLE_AUTHOR,
    ROLE_EDITOR,
    ROLE_REVIEWER,
    User,
)


class SignupSerializer(serializers.Serializer):
    """Serializer for user signup."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=255)
    affiliation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=ROLE_CHOICES),
        allow_empty=False,
    )
    why_to_be = serializers.CharField(required=False, allow_blank=True)

    def validate_roles(self, value):
        """Ensure roles are unique and valid."""
        seen = set()
        for r in value:
            if r in seen:
                raise serializers.ValidationError(f"Duplicate role: {r}")
            seen.add(r)
        return value

    def validate(self, attrs):
        """Require why_to_be when reviewer or editor selected."""
        roles = attrs.get("roles", [])
        why_to_be = attrs.get("why_to_be", "").strip()
        if ROLE_REVIEWER in roles or ROLE_EDITOR in roles:
            if not why_to_be:
                raise serializers.ValidationError(
                    {"why_to_be": "Required when selecting reviewer or editor role."}
                )
        return attrs

    def create(self, validated_data):
        """Create user with role approval logic."""
        roles = validated_data["roles"]
        why_to_be = validated_data.pop("why_to_be", "")

        reviewer_status = None
        editor_status = None
        if ROLE_REVIEWER in roles:
            reviewer_status = APPROVAL_PENDING
        if ROLE_EDITOR in roles:
            editor_status = APPROVAL_PENDING

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            affiliation=validated_data.get("affiliation", ""),
            country=validated_data.get("country", ""),
            roles=roles,
            reviewer_status=reviewer_status,
            editor_status=editor_status,
            why_to_be=why_to_be,
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile (GET/PATCH /api/me)."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "affiliation",
            "country",
            "orcid_id",
            "is_email_verified",
            "roles",
            "reviewer_status",
            "editor_status",
            "date_joined",
        ]
        read_only_fields = ["id", "email", "roles", "reviewer_status", "editor_status", "date_joined"]

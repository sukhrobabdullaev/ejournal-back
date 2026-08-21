"""Account serializers."""
import re
from urllib.parse import urlparse

from rest_framework import serializers

from journals.models import (
    MEMBERSHIP_STATUS_APPROVED,
    MEMBERSHIP_STATUS_PENDING,
    Journal,
    JournalMembership,
)

from .models import ROLE_CHOICES, ROLE_EDITOR, ROLE_REVIEWER, User


class SignupSerializer(serializers.Serializer):
    """Serializer for user signup."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=255)
    affiliation = serializers.CharField(max_length=255, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    journal_slug = serializers.SlugField(
        help_text="The journal the requested roles apply to.",
    )
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

    def validate_journal_slug(self, value):
        if not Journal.objects.filter(slug=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown journal.")
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
        """Create user, then create per-journal role membership rows."""
        roles = validated_data["roles"]
        why_to_be = validated_data.pop("why_to_be", "")
        journal = Journal.objects.get(slug=validated_data["journal_slug"])

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            affiliation=validated_data.get("affiliation", ""),
            country=validated_data.get("country", ""),
        )

        for role in roles:
            status = MEMBERSHIP_STATUS_APPROVED if role == "author" else MEMBERSHIP_STATUS_PENDING
            JournalMembership.objects.create(
                user=user,
                journal=journal,
                role=role,
                status=status,
                why_to_be=why_to_be,
            )

        return user


class JournalMembershipSummarySerializer(serializers.ModelSerializer):
    """Compact membership summary embedded in the /me response."""

    journal_slug = serializers.CharField(source="journal.slug", read_only=True)
    journal_name = serializers.CharField(source="journal.name", read_only=True)

    class Meta:
        model = JournalMembership
        fields = ["journal_slug", "journal_name", "role", "status"]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile (GET/PATCH /api/me)."""

    ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{4}$")

    memberships = JournalMembershipSummarySerializer(
        source="journal_memberships", many=True, read_only=True
    )

    def validate_google_scholar_url(self, value):
        """Accept only full Google Scholar profile/citation URLs."""
        value = (value or "").strip()
        if not value:
            return ""

        parsed = urlparse(value)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()

        if parsed.scheme not in {"http", "https"}:
            raise serializers.ValidationError("Google Scholar URL must start with http:// or https://")
        if "scholar.google." not in host:
            raise serializers.ValidationError("Use a valid Google Scholar URL.")
        if "/citations" not in path:
            raise serializers.ValidationError("Use your profile citation URL (contains /citations).")

        return value

    def validate_orcid_id(self, value):
        """Normalize ORCID format and reject invalid identifiers."""
        value = (value or "").strip()
        if not value:
            return ""

        cleaned = re.sub(r"[^0-9]", "", value)
        if len(cleaned) == 16:
            value = f"{cleaned[:4]}-{cleaned[4:8]}-{cleaned[8:12]}-{cleaned[12:]}"

        if not self.ORCID_PATTERN.match(value):
            raise serializers.ValidationError(
                "Invalid ORCID format. Use 0000-0000-0000-0000."
            )

        return value

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "affiliation",
            "country",
            "orcid_id",
            "google_scholar_url",
            "is_email_verified",
            "memberships",
            "date_joined",
        ]
        read_only_fields = ["id", "email", "memberships", "date_joined"]

"""Journal (tenant) serializers."""
from rest_framework import serializers

from .models import Journal


class JournalSerializer(serializers.ModelSerializer):
    """Public journal directory/branding serializer."""

    class Meta:
        model = Journal
        fields = [
            "slug",
            "name",
            "tagline",
            "logo",
            "accent_color",
            "contact_email",
        ]

"""Editorial board serializers."""
from rest_framework import serializers

from .models import EditorialBoardMember


class EditorialBoardMemberSerializer(serializers.ModelSerializer):
    """Public serializer for editorial board member."""

    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = EditorialBoardMember
        fields = [
            "id",
            "name",
            "affiliation",
            "expertise",
            "email",
            "linkedin_url",
            "profile_image_url",
            "role",
        ]

    def get_profile_image_url(self, obj):
        if not obj.profile_image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.profile_image.url)
        return obj.profile_image.url

"""Editorial board views (public API)."""
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import EditorialBoardMember, ROLE_ASSOCIATE_EDITOR, ROLE_EDITOR_IN_CHIEF, ROLE_MANAGING_EDITOR
from .serializers import EditorialBoardMemberSerializer


class EditorialBoardViewSet(viewsets.ReadOnlyModelViewSet):
    """Public list of editorial board members."""

    permission_classes = [AllowAny]
    serializer_class = EditorialBoardMemberSerializer

    def get_queryset(self):
        qs = EditorialBoardMember.objects.filter(is_active=True, journal=self.request.journal)
        role = self.request.query_params.get("role")
        if role in (ROLE_EDITOR_IN_CHIEF, ROLE_MANAGING_EDITOR, ROLE_ASSOCIATE_EDITOR):
            qs = qs.filter(role=role)
        return qs

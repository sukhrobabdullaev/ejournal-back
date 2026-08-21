"""Journal (tenant) views."""
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import Journal
from .serializers import JournalSerializer


class JournalViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/journals/ - Public journal directory.
    GET /api/journals/{slug}/ - Public journal branding lookup.
    """

    permission_classes = [AllowAny]
    serializer_class = JournalSerializer
    queryset = Journal.objects.filter(is_active=True)
    lookup_field = "slug"

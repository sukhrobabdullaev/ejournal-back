"""Journal directory URL routes (mounted at /api/journals/)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import JournalViewSet

router = DefaultRouter()
router.register("", JournalViewSet, basename="journal")

urlpatterns = [
    path("", include(router.urls)),
]

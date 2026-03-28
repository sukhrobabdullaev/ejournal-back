"""Review URL routes (mounted at /api/reviewer/)."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AcceptByTokenView, DeclineByTokenView, ReviewAssignmentViewSet

router = DefaultRouter()
router.register("assignments", ReviewAssignmentViewSet, basename="reviewer-assignment")
router.register("accept-by-token", AcceptByTokenView, basename="reviewer-accept-by-token")
router.register("decline-by-token", DeclineByTokenView, basename="reviewer-decline-by-token")

urlpatterns = [
    path("", include(router.urls)),
]

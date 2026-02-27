"""Editorial URL routes (mounted at /api/editor/)."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import EditorialReviewAssignmentViewSet, EditorialSubmissionViewSet

router = DefaultRouter()
router.register("submissions", EditorialSubmissionViewSet, basename="editor-submission")
router.register("review-assignments", EditorialReviewAssignmentViewSet, basename="editor-review-assignment")

urlpatterns = [
    path("", include(router.urls)),
]

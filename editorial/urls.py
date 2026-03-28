"""Editorial URL routes (mounted at /api/editor/)."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    EditorialReviewAssignmentViewSet,
    EditorialSubmissionViewSet,
    JournalIssueViewSet,
    ReviewerListView,
)

router = DefaultRouter()
router.register("submissions", EditorialSubmissionViewSet, basename="editor-submission")
router.register("review-assignments", EditorialReviewAssignmentViewSet, basename="editor-review-assignment")
router.register("issues", JournalIssueViewSet, basename="editor-issue")

urlpatterns = [
    path("reviewers", ReviewerListView.as_view(), name="editor-reviewer-list"),
    path("", include(router.urls)),
]

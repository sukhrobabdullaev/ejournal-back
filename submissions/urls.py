"""Submission URL routes."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ArticleDetailView,
    ArticleListView,
    PublishedIssueDetailView,
    PublishedIssueListView,
    SubmissionViewSet,
    TopicAreaViewSet,
)

router = DefaultRouter()
router.register("submissions", SubmissionViewSet, basename="submission")
router.register("topic-areas", TopicAreaViewSet, basename="topic-area")

urlpatterns = [
    path("articles/", ArticleListView.as_view(), name="article-list"),
    path("articles/<slug:slug>/", ArticleDetailView.as_view(), name="article-detail"),
    path("published/issues/", PublishedIssueListView.as_view(), name="published-issue-list"),
    path("published/issues/<int:issue_id>/", PublishedIssueDetailView.as_view(), name="published-issue-detail"),
    path("", include(router.urls)),
]

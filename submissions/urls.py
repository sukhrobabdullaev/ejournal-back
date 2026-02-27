"""Submission URL routes."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SubmissionViewSet, TopicAreaViewSet

router = DefaultRouter()
router.register("submissions", SubmissionViewSet, basename="submission")
router.register("topic-areas", TopicAreaViewSet, basename="topic-area")

urlpatterns = [
    path("", include(router.urls)),
]

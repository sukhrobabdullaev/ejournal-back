"""Editorial board URL routes."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import EditorialBoardViewSet

router = DefaultRouter()
router.register("", EditorialBoardViewSet, basename="editorial-board")

urlpatterns = [
    path("", include(router.urls)),
]

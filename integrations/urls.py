"""Integration URL routes."""
from django.urls import path

from .views import OrcidConnectView

urlpatterns = [
    path("orcid/connect", OrcidConnectView.as_view(), name="orcid-connect"),
]

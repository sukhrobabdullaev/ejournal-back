"""Integration URL routes."""
from django.urls import path

from .views import OrcidConnectView, UploadFileView

urlpatterns = [
    path("upload-file", UploadFileView.as_view(), name="upload-file"),
    path("orcid/connect", OrcidConnectView.as_view(), name="orcid-connect"),
]

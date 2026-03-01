"""Integration URL routes."""
from django.urls import path

from .views import UploadFileView

urlpatterns = [
    path("upload-file", UploadFileView.as_view(), name="upload-file"),
]

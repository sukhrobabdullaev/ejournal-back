"""
URL configuration for ejournal project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("ejournal.api_urls")),
]

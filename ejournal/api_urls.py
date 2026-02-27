"""
API URL routes.
"""
from django.http import JsonResponse
from django.urls import path, include

def api_root(request):
    """API root."""
    return JsonResponse({"message": "Ejournal API", "version": "1.0"})

urlpatterns = [
    path("", api_root),
    path("", include("accounts.urls")),
    path("", include("integrations.urls")),
    path("", include("submissions.urls")),
    path("reviewer/", include("reviews.urls")),
    path("editor/", include("editorial.urls")),
    path("admin/", include("accounts.admin_urls")),
]

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
    path("j/<slug:journal_slug>/", include("ejournal.journal_urls")),
    path("journals/", include("journals.urls")),
]

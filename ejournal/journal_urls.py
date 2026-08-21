"""Journal-scoped API URL routes (mounted at /api/j/<journal_slug>/)."""
from django.urls import path, include

urlpatterns = [
    path("", include("integrations.urls")),
    path("", include("submissions.urls")),
    path("certificates/", include("notifications.urls")),
    path("reviewer/", include("reviews.urls")),
    path("editor/", include("editorial.urls")),
    path("editorial-board/", include("editorial_board.urls")),
    path("admin/", include("accounts.admin_urls")),
]

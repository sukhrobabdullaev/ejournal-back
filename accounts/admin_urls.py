"""Admin API URL routes (mounted at /api/admin/)."""
from django.urls import path

from .admin_views import (
    ApproveEditorView,
    ApproveReviewerView,
    RejectEditorView,
    RejectReviewerView,
)

urlpatterns = [
    path("users/<int:user_id>/approve-reviewer", ApproveReviewerView.as_view(), name="admin-approve-reviewer"),
    path("users/<int:user_id>/approve-editor", ApproveEditorView.as_view(), name="admin-approve-editor"),
    path("users/<int:user_id>/reject-reviewer", RejectReviewerView.as_view(), name="admin-reject-reviewer"),
    path("users/<int:user_id>/reject-editor", RejectEditorView.as_view(), name="admin-reject-editor"),
]

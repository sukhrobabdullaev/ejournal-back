"""Review admin."""
from django.contrib import admin
from .models import Review, ReviewAssignment


@admin.register(ReviewAssignment)
class ReviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ["id", "submission", "reviewer", "invited_email", "status", "invited_at"]
    list_filter = ["status"]
    search_fields = ["submission__title", "reviewer__email", "invited_email"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "assignment", "recommendation", "submitted_at"]
    list_filter = ["recommendation"]

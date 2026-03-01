"""Editorial board admin."""
from django.contrib import admin

from .models import EditorialBoardMember


@admin.register(EditorialBoardMember)
class EditorialBoardMemberAdmin(admin.ModelAdmin):
    list_display = ["name", "role", "affiliation", "order", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["name", "affiliation", "email"]
    ordering = ["role", "order", "name"]

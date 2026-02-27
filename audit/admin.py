"""Audit admin."""
from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["id", "action_type", "target_type", "target_id", "actor_user", "created_at"]
    list_filter = ["action_type", "target_type"]
    search_fields = ["target_id", "action_type"]
    readonly_fields = ["actor_user", "action_type", "target_type", "target_id", "old_value", "new_value", "created_at"]

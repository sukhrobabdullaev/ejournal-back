"""Journal (tenant) admin - platform superadmin management."""
from django.contrib import admin

from .models import Journal, JournalMembership


class JournalMembershipInline(admin.TabularInline):
    """Assign/approve users' roles for this journal directly from the Journal page."""

    model = JournalMembership
    extra = 1
    autocomplete_fields = ["user"]
    fields = ["user", "role", "status", "approved_at"]


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    """Platform superadmin: create and configure journals."""

    list_display = ["name", "slug", "doi_prefix", "contact_email", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [JournalMembershipInline]


@admin.register(JournalMembership)
class JournalMembershipAdmin(admin.ModelAdmin):
    """Direct list view for cross-journal membership auditing/bulk approval."""

    list_display = ["user", "journal", "role", "status", "approved_at"]
    list_filter = ["journal", "role", "status"]
    search_fields = ["user__email", "user__full_name"]
    autocomplete_fields = ["user", "journal"]

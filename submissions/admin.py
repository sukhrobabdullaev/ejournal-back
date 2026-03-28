"""Submission admin."""
from django.contrib import admin
from .models import JournalIssue, Submission, SubmissionSupplementaryFile, SubmissionVersion, TopicArea


@admin.register(TopicArea)
class TopicAreaAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


class SubmissionSupplementaryFileInline(admin.TabularInline):
    model = SubmissionSupplementaryFile
    extra = 0


class SubmissionVersionInline(admin.TabularInline):
    model = SubmissionVersion
    extra = 0
    readonly_fields = ["version_number", "created_at"]


@admin.register(SubmissionVersion)
class SubmissionVersionAdmin(admin.ModelAdmin):
    list_display = ["id", "submission", "version_number", "created_at"]
    list_filter = ["submission"]


@admin.register(JournalIssue)
class JournalIssueAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "volume",
        "issue_number",
        "publication_year",
        "publication_date",
        "created_at",
    ]
    list_filter = ["publication_year", "volume"]
    search_fields = ["title"]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "author", "status", "editorial_decision", "created_at"]
    list_filter = ["status", "issue"]
    search_fields = ["title", "author__email"]
    inlines = [SubmissionSupplementaryFileInline, SubmissionVersionInline]

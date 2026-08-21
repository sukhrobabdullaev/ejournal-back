"""Resolve the current Journal from the URL and attach it to the request."""
import re

from django.http import JsonResponse

from .models import Journal

_JOURNAL_SLUG_RE = re.compile(r"^/api/j/(?P<journal_slug>[-\w]+)/")


class JournalContextMiddleware:
    """Attaches `request.journal` (a Journal instance or None) based on the
    `/api/j/<journal_slug>/...` URL prefix.

    Returns 404 if the slug doesn't match an active journal, so every
    journal-scoped view fails closed rather than silently operating on
    `request.journal = None`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        match = _JOURNAL_SLUG_RE.match(request.path_info)
        if match:
            slug = match.group("journal_slug")
            try:
                request.journal = Journal.objects.get(slug=slug, is_active=True)
            except Journal.DoesNotExist:
                return JsonResponse({"detail": f"Unknown journal '{slug}'."}, status=404)
        else:
            request.journal = None
        return self.get_response(request)

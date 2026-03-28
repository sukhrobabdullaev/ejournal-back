"""Submission views (author workflow)."""
import re
import uuid

from django.core.files.base import ContentFile
from django.db.models import Max
from django.db import transaction
from django.utils.text import slugify
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAuthor, IsEmailVerified

from .models import STATUS_RESUBMITTED, STATUS_REVISION_REQUIRED, STATUS_SUBMITTED, Submission, SubmissionSupplementaryFile, SubmissionVersion, TopicArea
from .models import JournalIssue, STATUS_PUBLISHED
from .serializers import SubmissionSerializer, TopicAreaSerializer
from .transitions import validate_transition
from .validation import validate_submission_ready_for_submit


class SubmissionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Author submission CRUD and actions."""

    permission_classes = [IsAuthor]
    serializer_class = SubmissionSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return (
            Submission.objects
            .filter(author=self.request.user)
            .select_related("topic_area")
            .prefetch_related(
                "supplementary_files",
                "recognition_certificates",
                "journal_publication_certificates",
            )
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """POST /api/submissions - Create submission in submitted state."""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save(author=request.user, status=STATUS_SUBMITTED)
        from audit.services import log
        log(actor_user=request.user, action_type="submission_created", target_type="submission", target_id=submission.id)
        serializer_out = self.get_serializer(submission)
        return Response(serializer_out.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """GET /api/submissions/mine - List own submissions."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """GET /api/submissions/{id}."""
        return super().retrieve(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """PATCH /api/submissions/{id} - Incremental save of step fields."""
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Disable PUT; use PATCH for partial updates."""
        if request.method == "PUT":
            return Response({"detail": "Use PATCH for partial updates."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="upload-file")
    def upload_file(self, request, pk=None):
        """POST /api/submissions/{id}/upload-file - Upload file via form-data (file, file_type). Returns file URL."""
        submission = self.get_object()
        if submission.status not in (STATUS_SUBMITTED, STATUS_REVISION_REQUIRED):
            return Response(
                {"detail": "Files can only be uploaded for submitted or revision_required records."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        file_type = (request.data.get("file_type") or "manuscript").strip() or "manuscript"
        if file_type not in ("manuscript", "supplementary"):
            return Response(
                {"detail": "file_type must be 'manuscript' or 'supplementary'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"detail": "Provide 'file' in form-data. file_type: manuscript | supplementary"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        content = file_obj.read()
        filename = file_obj.name or "file"

        if file_type == "manuscript":
            ext = filename.rsplit(".", 1)[-1] if "." in filename else "pdf"
            safe_name = f"{uuid.uuid4().hex}.{ext}"
            submission.manuscript_pdf.save(safe_name, ContentFile(content), save=True)
            url = request.build_absolute_uri(submission.manuscript_pdf.url) if submission.manuscript_pdf else None
            return Response({"url": url, "file_type": "manuscript"})
        else:
            safe_name = f"{uuid.uuid4().hex}_{filename}"
            supp = SubmissionSupplementaryFile.objects.create(
                submission=submission,
                file=ContentFile(content, name=safe_name),
                name=filename,
            )
            url = request.build_absolute_uri(supp.file.url) if supp.file else None
            return Response({"url": url, "file_type": "supplementary", "id": supp.id})

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        """POST /api/submissions/{id}/submit - Finalize initial submitted record and create version."""
        submission = self.get_object()
        if submission.status != STATUS_SUBMITTED:
            return Response(
                {"detail": "Only submitted records can be finalized via this endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if submission.versions.exists():
            return Response(
                {"detail": "Initial submission is already finalized."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_submission_ready_for_submit(submission)
        except Exception as e:
            msg = str(getattr(e, "detail", e))
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            from audit.services import log
            log(
                actor_user=request.user,
                action_type="submission_submitted",
                target_type="submission",
                target_id=submission.id,
                old_value={"status": STATUS_SUBMITTED},
                new_value={"status": STATUS_SUBMITTED},
            )

            from notifications.services import queue_submission_submitted
            queue_submission_submitted(submission.id, submission.author.email, submission.author.id)

            # Create initial SubmissionVersion
            supp_snapshot = [
                {"name": s.name, "url": s.file.url if s.file else None}
                for s in submission.supplementary_files.all()
            ]
            SubmissionVersion.objects.create(
                submission=submission,
                version_number=1,
                manuscript_pdf=submission.manuscript_pdf,
                supplementary_files_snapshot=supp_snapshot,
            )

        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="resubmit")
    def resubmit(self, request, pk=None):
        """POST /api/submissions/{id}/resubmit - revision_required -> resubmitted (after author updates)."""
        submission = self.get_object()
        try:
            validate_transition(submission.status, STATUS_RESUBMITTED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_submission_ready_for_submit(submission)
        except Exception as e:
            msg = str(getattr(e, "detail", e))
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            old_status = submission.status
            submission.status = STATUS_RESUBMITTED
            submission.save(update_fields=["status"])

            from audit.services import log
            log(actor_user=request.user, action_type="submission_resubmitted", target_type="submission", target_id=submission.id, old_value={"status": old_status}, new_value={"status": STATUS_RESUBMITTED})

            from notifications.services import queue_submission_submitted
            queue_submission_submitted(submission.id, submission.author.email, submission.author.id)

            next_version = (submission.versions.aggregate(max_v=Max("version_number"))["max_v"] or 0) + 1
            supp_snapshot = [
                {"name": s.name, "url": s.file.url if s.file else None}
                for s in submission.supplementary_files.all()
            ]
            SubmissionVersion.objects.create(
                submission=submission,
                version_number=next_version,
                manuscript_pdf=submission.manuscript_pdf,
                supplementary_files_snapshot=supp_snapshot,
            )

        serializer = self.get_serializer(submission)
        return Response(serializer.data)


class TopicAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/topic-areas - List topic areas (for submission form)."""

    permission_classes = [IsAuthenticated, IsEmailVerified]
    serializer_class = TopicAreaSerializer
    queryset = TopicArea.objects.all()


def _build_article_slug(submission: Submission) -> str:
    """Build a stable public slug that includes submission id for reverse lookup."""
    base = slugify(submission.title or "")[:80] or "article"
    return f"{base}-{submission.id}"


def _public_article_payload(submission: Submission, request) -> dict:
    """Map a published submission into frontend article shape."""
    topic_name = submission.topic_area.name if submission.topic_area else None
    manuscript_url = ""
    if submission.manuscript_pdf:
        try:
            manuscript_url = request.build_absolute_uri(submission.manuscript_pdf.url)
        except Exception:
            manuscript_url = ""

    return {
        "id": str(submission.id),
        "slug": _build_article_slug(submission),
        "title": submission.title or "Untitled",
        "abstract": submission.abstract or "",
        "keywords": submission.keywords or [],
        "topic_tags": [topic_name] if topic_name else [],
        "authors": [
            {
                "full_name": submission.author.full_name,
                "affiliation": submission.author.affiliation,
                "orcid": submission.author.orcid_id,
                "is_corresponding": True,
                "author_order": 1,
            }
        ],
        "published_at": submission.updated_at,
        "received_at": submission.created_at,
        "accepted_at": None,
        "doi": None,
        "pdf_public_url": manuscript_url,
        "status": submission.status,
        "issue_id": submission.issue_id,
        "issue_order": submission.issue_order,
        "page_start": submission.page_start,
        "page_end": submission.page_end,
    }


def _extract_submission_id_from_slug(slug: str) -> int | None:
    """Extract trailing numeric id from article slug."""
    if slug.isdigit():
        return int(slug)
    match = re.search(r"-(\d+)$", slug)
    return int(match.group(1)) if match else None


class ArticleListView(APIView):
    """GET /api/articles - Public list of published submissions as articles."""

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        queryset = (
            Submission.objects.filter(status=STATUS_PUBLISHED)
            .select_related("author", "topic_area")
            .order_by("-updated_at")
        )
        payload = [_public_article_payload(submission, request) for submission in queryset]
        return Response(payload, status=status.HTTP_200_OK)


class ArticleDetailView(APIView):
    """GET /api/articles/{slug} - Public detail for a published article."""

    permission_classes = [AllowAny]

    def get(self, request, slug, *args, **kwargs):
        submission_id = _extract_submission_id_from_slug(slug)
        if not submission_id:
            return Response({"detail": "Article not found."}, status=status.HTTP_404_NOT_FOUND)

        submission = (
            Submission.objects.filter(id=submission_id, status=STATUS_PUBLISHED)
            .select_related("author", "topic_area")
            .first()
        )
        if not submission:
            return Response({"detail": "Article not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = _public_article_payload(submission, request)
        return Response(payload, status=status.HTTP_200_OK)


def _issue_pdf_url(issue: JournalIssue, request) -> str | None:
    if not issue.full_issue_pdf:
        return None
    try:
        url = issue.full_issue_pdf.url
    except Exception:
        return None
    return request.build_absolute_uri(url)


def _public_issue_payload(issue: JournalIssue, request, include_articles: bool = False) -> dict:
    payload = {
        "id": issue.id,
        "title": issue.title,
        "volume": issue.volume,
        "issue_number": issue.issue_number,
        "publication_year": issue.publication_year,
        "publication_date": issue.publication_date,
        "full_issue_pdf_url": _issue_pdf_url(issue, request),
        "created_at": issue.created_at,
        "updated_at": issue.updated_at,
    }

    if not include_articles:
        return payload

    articles_qs = (
        issue.articles
        .filter(status=STATUS_PUBLISHED)
        .select_related("author")
        .order_by("issue_order", "id")
    )

    def _pdf_page_count(article: Submission) -> int | None:
        if not article.manuscript_pdf:
            return None
        try:
            from PyPDF2 import PdfReader

            article.manuscript_pdf.open("rb")
            reader = PdfReader(article.manuscript_pdf)
            return len(reader.pages)
        except Exception:
            return None
        finally:
            try:
                article.manuscript_pdf.close()
            except Exception:
                pass

    payload["articles"] = [
        {
            "id": article.id,
            "slug": _build_article_slug(article),
            "title": article.title or "Untitled",
            "authors": [
                {
                    "full_name": article.author.full_name,
                    "affiliation": article.author.affiliation,
                }
            ],
            "page_start": article.page_start,
            "page_end": article.page_end,
            "manuscript_page_count": _pdf_page_count(article),
            "pdf_public_url": request.build_absolute_uri(article.manuscript_pdf.url) if article.manuscript_pdf else None,
            "status": article.status,
        }
        for article in articles_qs
    ]
    return payload


class PublishedIssueListView(APIView):
    """GET /api/published/issues - Public list of published issues."""

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        queryset = (
            JournalIssue.objects
            .filter(articles__status=STATUS_PUBLISHED)
            .distinct()
            .order_by("-publication_year", "-volume", "-issue_number")
        )
        payload = [_public_issue_payload(issue, request, include_articles=False) for issue in queryset]
        return Response(payload, status=status.HTTP_200_OK)


class PublishedIssueDetailView(APIView):
    """GET /api/published/issues/{id} - Public issue detail with TOC."""

    permission_classes = [AllowAny]

    def get(self, request, issue_id, *args, **kwargs):
        issue = (
            JournalIssue.objects
            .filter(id=issue_id)
            .first()
        )
        if not issue:
            return Response({"detail": "Issue not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = _public_issue_payload(issue, request, include_articles=True)
        return Response(payload, status=status.HTTP_200_OK)

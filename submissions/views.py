"""Submission views (author workflow)."""
import base64
import uuid

from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAuthor

from .models import STATUS_SUBMITTED, Submission, SubmissionSupplementaryFile, SubmissionVersion, TopicArea
from .serializers import SubmissionSerializer, TopicAreaSerializer
from .transitions import validate_transition
from .validation import validate_submission_ready_for_submit


class SubmissionViewSet(viewsets.ModelViewSet):
    """Author submission CRUD and actions."""

    permission_classes = [IsAuthor]
    serializer_class = SubmissionSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return Submission.objects.filter(author=self.request.user).select_related("topic_area").prefetch_related("supplementary_files")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """POST /api/submissions - Create draft."""
        submission = Submission.objects.create(
            author=request.user,
            status="draft",
        )
        from audit.services import log
        log(actor_user=request.user, action_type="submission_created", target_type="submission", target_id=submission.id)
        serializer = self.get_serializer(submission)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
        return Response({"detail": "Use PATCH for partial updates."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        """Only drafts can be deleted (optional policy)."""
        submission = self.get_object()
        if submission.status != "draft":
            return Response(
                {"detail": "Only drafts can be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="upload-file")
    def upload_file(self, request, pk=None):
        """POST /api/submissions/{id}/upload-file - Upload file. Use form-data (file, file_type) or JSON (base64). Returns file URL."""
        submission = self.get_object()
        if submission.status != "draft":
            return Response(
                {"detail": "Files can only be uploaded for drafts."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        file_type = (request.data.get("file_type") or "manuscript").strip() or "manuscript"
        if file_type not in ("manuscript", "supplementary"):
            return Response(
                {"detail": "file_type must be 'manuscript' or 'supplementary'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_obj = request.FILES.get("file")
        if file_obj:
            content = file_obj.read()
            filename = file_obj.name or "file"
        else:
            file_base64 = request.data.get("file_base64")
            filename = request.data.get("filename", "file")
            if not file_base64:
                return Response(
                    {"detail": "Provide 'file' (form-data) or 'file_base64' + 'filename' (JSON). file_type: manuscript | supplementary"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                content = base64.b64decode(file_base64, validate=True)
            except Exception:
                return Response({"detail": "Invalid base64 encoding."}, status=status.HTTP_400_BAD_REQUEST)
            if not content:
                return Response({"detail": "Empty file content."}, status=status.HTTP_400_BAD_REQUEST)

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
        """POST /api/submissions/{id}/submit - Transition draft -> submitted."""
        submission = self.get_object()

        try:
            validate_submission_ready_for_submit(submission)
        except Exception as e:
            msg = str(getattr(e, "detail", e))
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_transition(submission.status, STATUS_SUBMITTED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            old_status = submission.status
            submission.status = STATUS_SUBMITTED
            submission.save(update_fields=["status"])

            from audit.services import log
            log(actor_user=request.user, action_type="submission_submitted", target_type="submission", target_id=submission.id, old_value={"status": old_status}, new_value={"status": STATUS_SUBMITTED})

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


class TopicAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/topic-areas - List topic areas (for submission form)."""

    permission_classes = [IsAuthenticated]
    serializer_class = TopicAreaSerializer
    queryset = TopicArea.objects.all()

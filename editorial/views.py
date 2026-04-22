"""Editorial views."""
import logging
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from PyPDF2 import PdfMerger
from PyPDF2.errors import PdfReadError
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from accounts.models import APPROVAL_APPROVED, ROLE_REVIEWER, User
from accounts.permissions import IsApprovedEditor
from reviews.models import ReviewAssignment, STATUS_INVITED
from submissions.models import (
    JournalIssue,
    STATUS_ACCEPTED,
    STATUS_DECISION_PENDING,
    STATUS_DESK_REJECTED,
    STATUS_PUBLISHED,
    STATUS_REJECTED,
    STATUS_REVISION_REQUIRED,
    STATUS_SCREENING,
    STATUS_UNDER_REVIEW,
    Submission,
    SubmissionVersion,
)
from submissions.doi import ensure_local_doi
from submissions.transitions import validate_transition

from .serializers import (
    AcceptedSubmissionOptionSerializer,
    DecisionSerializer,
    DeskRejectSerializer,
    EditorialSubmissionSerializer,
    InviteReviewerSerializer,
    JournalIssueDetailSerializer,
    JournalIssueUpsertSerializer,
    ReviewerOptionSerializer,
)

logger = logging.getLogger(__name__)


def get_first_submission_page_size(submissions: list[Submission]) -> tuple[float, float]:
    """Read first manuscript page size to match cover dimensions."""
    if not submissions:
        return A4

    manuscript = submissions[0].manuscript_pdf
    if not manuscript:
        return A4

    try:
        from PyPDF2 import PdfReader

        manuscript.open("rb")
        pdf_bytes = manuscript.read()
        reader = PdfReader(BytesIO(pdf_bytes))
        if not reader.pages:
            return A4
        first_page = reader.pages[0]
        width = float(first_page.mediabox.width)
        height = float(first_page.mediabox.height)
        return (width, height)
    except PdfReadError as exc:
        logger.exception("Invalid first manuscript PDF for issue cover sizing.")
        raise ValidationError(
            {
                "detail": (
                    f"Submission #{submissions[0].id} has an invalid manuscript PDF. "
                    "Please re-upload a valid PDF file before making the journal issue."
                )
            }
        ) from exc
    except Exception:
        logger.exception("Failed to detect first manuscript page size; fallback to A4.")
        return A4
    finally:
        try:
            manuscript.close()
        except Exception:
            pass


def build_issue_cover_pdf(page_size: tuple[float, float]) -> bytes:
    """Render configured cover image into a single PDF page with requested size."""
    cover_path = Path(settings.ISSUE_COVER_IMAGE_PATH)
    if not cover_path.exists():
        raise ValidationError(
            {"detail": f"Issue cover image not found: {cover_path}"}
        )

    try:
        output = BytesIO()
        c = canvas.Canvas(output, pagesize=page_size)
        page_width, page_height = page_size
        c.drawImage(
            ImageReader(str(cover_path)),
            0,
            0,
            width=page_width,
            height=page_height,
            preserveAspectRatio=False,
            mask="auto",
        )
        c.showPage()
        c.save()
        return output.getvalue()
    except Exception as exc:
        logger.exception("Failed to build issue cover PDF from image: %s", cover_path)
        raise ValidationError(
            {"detail": "Failed to render issue cover image."}
        ) from exc


def merge_submission_pdfs(submissions: list[Submission]) -> bytes:
    """Merge manuscript PDFs into one binary PDF blob."""
    merger = PdfMerger()
    opened_files = []

    try:
        cover_pdf = build_issue_cover_pdf(get_first_submission_page_size(submissions))
        merger.append(BytesIO(cover_pdf))

        for submission in submissions:
            manuscript = submission.manuscript_pdf
            if not manuscript:
                raise ValidationError(
                    {"detail": f"Submission #{submission.id} has no manuscript PDF."}
                )
            manuscript.open("rb")
            pdf_bytes = manuscript.read()
            opened_files.append(manuscript)
            if not pdf_bytes:
                raise ValidationError(
                    {"detail": f"Submission #{submission.id} has an empty manuscript PDF."}
                )

            try:
                from PyPDF2 import PdfReader

                PdfReader(BytesIO(pdf_bytes))
            except PdfReadError as exc:
                raise ValidationError(
                    {
                        "detail": (
                            f"Submission #{submission.id} ('{submission.title or 'Untitled'}') has an invalid manuscript PDF. "
                            "Please re-upload a valid PDF file."
                        )
                    }
                ) from exc

            try:
                merger.append(BytesIO(pdf_bytes))
            except PdfReadError as exc:
                raise ValidationError(
                    {
                        "detail": (
                            f"Submission #{submission.id} ('{submission.title or 'Untitled'}') could not be merged because its PDF is corrupted or incomplete (EOF marker missing). "
                            "Please re-upload a valid PDF file."
                        )
                    }
                ) from exc

        output = BytesIO()
        merger.write(output)
        return output.getvalue()
    except Exception as exc:
        logger.exception("Issue PDF merge failed.")
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError({"detail": "Failed to merge manuscript PDFs."}) from exc
    finally:
        merger.close()
        for file_obj in opened_files:
            try:
                file_obj.close()
            except Exception:
                logger.warning("Failed to close manuscript file handle.")


def get_submission_pdf_page_count(submission: Submission) -> int:
    """Read manuscript PDF and return page count."""
    manuscript = submission.manuscript_pdf
    if not manuscript:
        raise ValidationError({"detail": f"Submission #{submission.id} has no manuscript PDF."})
    try:
        from PyPDF2 import PdfReader

        manuscript.open("rb")
        pdf_bytes = manuscript.read()
        reader = PdfReader(BytesIO(pdf_bytes))
        page_count = len(reader.pages)
        return page_count if page_count > 0 else 1
    except PdfReadError as exc:
        logger.exception("Invalid manuscript PDF for submission_id=%s", submission.id)
        raise ValidationError(
            {
                "detail": (
                    f"Submission #{submission.id} ('{submission.title or 'Untitled'}') contains an invalid PDF. "
                    "Please replace the manuscript file and try again."
                )
            }
        ) from exc
    except Exception as exc:
        logger.exception("Failed to read manuscript pages for submission_id=%s", submission.id)
        raise ValidationError(
            {"detail": f"Cannot read PDF pages for submission #{submission.id}."}
        ) from exc
    finally:
        try:
            manuscript.close()
        except Exception:
            pass


def get_submission_queryset():
    """Submissions visible to editors (initial finalize completed)."""
    return (
        Submission.objects
        .filter(versions__isnull=False)
        .select_related("author", "topic_area")
        .prefetch_related("supplementary_files", "review_assignments", "review_assignments__review")
        .distinct()
    )


class EditorialSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Editor submission management."""

    permission_classes = [IsApprovedEditor]
    serializer_class = EditorialSubmissionSerializer

    def get_queryset(self):
        qs = get_submission_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def list(self, request, *args, **kwargs):
        """GET /api/editor/submissions?status= - List submissions."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """GET /api/editor/submissions/{id} - Get submission detail."""
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="start-screening")
    def start_screening(self, request, pk=None):
        """POST /api/editor/submissions/{id}/start-screening - submitted -> screening."""
        submission = self.get_object()
        try:
            validate_transition(submission.status, STATUS_SCREENING)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            old_status = submission.status
            submission.status = STATUS_SCREENING
            submission.save(update_fields=["status"])
            from audit.services import log
            log(actor_user=request.user, action_type="status_transition", target_type="submission", target_id=submission.id, old_value={"status": old_status}, new_value={"status": STATUS_SCREENING})

            from notifications.services import queue_status_changed
            queue_status_changed(
                submission.id, old_status, STATUS_SCREENING,
                submission.author.email, submission.author_id,
                idempotency_key=f"status_{submission.id}_{old_status}_{STATUS_SCREENING}",
            )

        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="desk-reject")
    def desk_reject(self, request, pk=None):
        """POST /api/editor/submissions/{id}/desk-reject - screening -> desk_rejected."""
        submission = self.get_object()
        serializer = DeskRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        try:
            validate_transition(submission.status, STATUS_DESK_REJECTED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            old_status = submission.status
            submission.status = STATUS_DESK_REJECTED
            submission.desk_reject_reason = reason
            submission.save(update_fields=["status", "desk_reject_reason"])
            from audit.services import log
            log(actor_user=request.user, action_type="status_transition", target_type="submission", target_id=submission.id, old_value={"status": old_status}, new_value={"status": STATUS_DESK_REJECTED, "reason": reason})

            from notifications.services import queue_status_changed
            queue_status_changed(
                submission.id,
                old_status,
                STATUS_DESK_REJECTED,
                submission.author.email,
                submission.author_id,
                idempotency_key=f"status_{submission.id}_{old_status}_{STATUS_DESK_REJECTED}",
                reason=reason,
            )

        serializer_out = self.get_serializer(submission)
        return Response(serializer_out.data)

    @action(detail=True, methods=["post"], url_path="send-to-review")
    def send_to_review(self, request, pk=None):
        """POST /api/editor/submissions/{id}/send-to-review - screening -> under_review."""
        submission = self.get_object()
        try:
            validate_transition(submission.status, STATUS_UNDER_REVIEW)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            old_status = submission.status
            submission.status = STATUS_UNDER_REVIEW
            submission.save(update_fields=["status"])
            from audit.services import log
            log(actor_user=request.user, action_type="status_transition", target_type="submission", target_id=submission.id, old_value={"status": old_status}, new_value={"status": STATUS_UNDER_REVIEW})

            from notifications.services import queue_status_changed
            queue_status_changed(
                submission.id, old_status, STATUS_UNDER_REVIEW,
                submission.author.email, submission.author_id,
                idempotency_key=f"status_{submission.id}_{old_status}_{STATUS_UNDER_REVIEW}",
            )

        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="invite-reviewer")
    def invite_reviewer(self, request, pk=None):
        """POST /api/editor/submissions/{id}/invite-reviewer - Invite reviewer."""
        submission = self.get_object()
        serializer = InviteReviewerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if submission.status not in (STATUS_SCREENING, STATUS_UNDER_REVIEW):
            return Response(
                {"detail": "Can only invite reviewers for screening or under_review submissions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        version = submission.versions.order_by("-version_number").first()
        if not version:
            return Response(
                {"detail": "No submission version found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reviewer_user_id = serializer.validated_data.get("reviewer_user_id")
        reviewer_email = serializer.validated_data.get("reviewer_email", "").strip()
        due_date = serializer.validated_data.get("due_date")

        reviewer = None
        invited_email = ""
        if reviewer_user_id:
            reviewer = User.objects.filter(id=reviewer_user_id).first()
            if not reviewer:
                return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
            if not reviewer.is_approved_reviewer():
                return Response(
                    {"detail": "User is not an approved reviewer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            invited_email = reviewer.email
        else:
            invited_email = reviewer_email

        if not invited_email:
            return Response({"detail": "Reviewer email required."}, status=status.HTTP_400_BAD_REQUEST)

        if ReviewAssignment.objects.filter(
            submission=submission,
            submission_version=version,
            invited_email=invited_email,
        ).exists():
            return Response(
                {"detail": "Reviewer already invited for this submission/version."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment = ReviewAssignment.objects.create(
            submission=submission,
            submission_version=version,
            reviewer=reviewer,
            invited_email=invited_email,
            status=STATUS_INVITED,
            due_date=due_date,
        )
        from audit.services import log
        log(actor_user=request.user, action_type="reviewer_invited", target_type="review_assignment", target_id=assignment.id, new_value={"submission_id": submission.id, "invited_email": invited_email})

        from notifications.services import queue_reviewer_invited
        queue_reviewer_invited(
            assignment.id,
            invited_email,
            submission.title or "Untitled",
            assignment.token,
        )

        return Response(
            {
                "id": assignment.id,
                "reviewer": reviewer.id if reviewer else None,
                "invited_email": invited_email,
                "token": assignment.token,
                "due_date": assignment.due_date,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="move-to-decision")
    def move_to_decision(self, request, pk=None):
        """POST /api/editor/submissions/{id}/move-to-decision - under_review -> decision_pending."""
        submission = self.get_object()
        try:
            validate_transition(submission.status, STATUS_DECISION_PENDING)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            old_status = submission.status
            submission.status = STATUS_DECISION_PENDING
            submission.save(update_fields=["status"])
            from audit.services import log
            log(actor_user=request.user, action_type="status_transition", target_type="submission", target_id=submission.id, old_value={"status": old_status}, new_value={"status": STATUS_DECISION_PENDING})

            from notifications.services import queue_status_changed
            queue_status_changed(
                submission.id, old_status, STATUS_DECISION_PENDING,
                submission.author.email, submission.author_id,
                idempotency_key=f"status_{submission.id}_{old_status}_{STATUS_DECISION_PENDING}",
            )

        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def decision(self, request, pk=None):
        """POST /api/editor/submissions/{id}/decision - Make accept/reject/revision_required."""
        submission = self.get_object()
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decision = serializer.validated_data["decision"]
        decision_letter = serializer.validated_data["decision_letter"]

        status_map = {
            "accept": STATUS_ACCEPTED,
            "reject": STATUS_REJECTED,
            "revision_required": STATUS_REVISION_REQUIRED,
        }
        new_status = status_map[decision]

        try:
            validate_transition(submission.status, new_status)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            old_status = submission.status
            submission.status = new_status
            submission.editorial_decision = decision
            submission.decision_letter = decision_letter
            submission.save(update_fields=["status", "editorial_decision", "decision_letter"])
            from audit.services import log
            log(actor_user=request.user, action_type="decision", target_type="submission", target_id=submission.id, old_value={"status": old_status}, new_value={"status": new_status, "decision": decision})

            from notifications.services import (
                queue_revision_requested,
                queue_submission_accepted,
                queue_submission_rejected,
            )
            author = submission.author
            if decision == "revision_required":
                queue_revision_requested(submission.id, author.email, author.id, decision_letter)
            elif decision == "accept":
                queue_submission_accepted(submission.id, author.email, author.id)
                review_ids = list(
                    submission.review_assignments.filter(review__isnull=False).values_list(
                        "review__id", flat=True
                    )
                )
                if review_ids:
                    from notifications.tasks import send_author_reviewer_recognition_certificate

                    for review_id in review_ids:
                        try:
                            send_author_reviewer_recognition_certificate.delay(review_id)
                        except Exception:
                            logger.exception(
                                "Failed to queue reviewer recognition certificate for review_id=%s",
                                review_id,
                            )
            elif decision == "reject":
                queue_submission_rejected(submission.id, author.email, author.id, decision_letter)

        serializer_out = self.get_serializer(submission)
        return Response(serializer_out.data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """POST /api/editor/submissions/{id}/publish - accepted -> published."""
        from submissions.models import STATUS_PUBLISHED

        submission = self.get_object()
        try:
            validate_transition(submission.status, STATUS_PUBLISHED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            old_status = submission.status
            submission.status = STATUS_PUBLISHED
            ensure_local_doi(submission, save=False)
            submission.save(update_fields=["status", "doi", "doi_status", "updated_at"])
            from audit.services import log
            log(actor_user=request.user, action_type="publish", target_type="submission", target_id=submission.id, old_value={"status": old_status}, new_value={"status": STATUS_PUBLISHED})

            from notifications.services import queue_submission_published
            queue_submission_published(submission.id, submission.author.email, submission.author.id)

        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="generate-doi")
    def generate_doi(self, request, pk=None):
        """POST /api/editor/submissions/{id}/generate-doi - Generate local DOI for accepted/published submission."""
        submission = self.get_object()
        if submission.status not in (STATUS_ACCEPTED, STATUS_PUBLISHED):
            return Response(
                {"detail": "DOI can only be generated for accepted or published submissions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doi_value = ensure_local_doi(submission, save=True)
        return Response(
            {
                "id": submission.id,
                "doi": doi_value,
                "doi_status": submission.doi_status,
            },
            status=status.HTTP_200_OK,
        )


class EditorialReviewAssignmentViewSet(viewsets.ViewSet):
    """Editor actions on review assignments."""

    permission_classes = [IsApprovedEditor]

    @action(detail=True, methods=["post"])
    def remind(self, request, pk=None):
        """POST /api/editor/review-assignments/{id}/remind - Stub (Phase 6 will send email)."""
        assignment = ReviewAssignment.objects.filter(id=pk).select_related("submission").first()
        if not assignment:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if assignment.status not in (STATUS_INVITED, STATUS_ACCEPTED):
            return Response(
                {"detail": "Can only remind invited or accepted assignments."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from notifications.services import queue_review_reminder_email
        queue_review_reminder_email(assignment.id)
        return Response(
            {"detail": "Reminder queued.", "assignment_id": assignment.id},
            status=status.HTTP_200_OK,
        )


class JournalIssueViewSet(viewsets.ModelViewSet):
    """Editor-only issue builder endpoints (Make Journal)."""

    permission_classes = [IsApprovedEditor]
    serializer_class = JournalIssueDetailSerializer
    queryset = JournalIssue.objects.prefetch_related("articles", "articles__author").all()
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return JournalIssueUpsertSerializer
        if self.action == "accepted_submissions":
            return AcceptedSubmissionOptionSerializer
        return JournalIssueDetailSerializer

    @action(detail=False, methods=["get"], url_path="accepted-submissions")
    def accepted_submissions(self, request):
        """List accepted/published submissions available for issue publishing/editing."""
        queryset = (
            Submission.objects
            .filter(status__in=[STATUS_ACCEPTED, STATUS_PUBLISHED], issue__isnull=True)
            .select_related("author")
            .order_by("-updated_at")
        )
        serializer = AcceptedSubmissionOptionSerializer(
            queryset,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _resolve_submissions_for_issue(self, issue, article_items):
        submission_ids = [item["submission_id"] for item in article_items]
        submissions = (
            Submission.objects
            .filter(id__in=submission_ids)
            .select_related("author")
        )
        submission_map = {submission.id: submission for submission in submissions}
        missing = [submission_id for submission_id in submission_ids if submission_id not in submission_map]
        if missing:
            raise ValidationError({"detail": f"Submissions not found: {', '.join(map(str, missing))}"})

        resolved_items = []
        for payload in sorted(article_items, key=lambda item: item["order"]):
            submission = submission_map[payload["submission_id"]]
            is_existing_article = bool(issue and submission.issue_id == issue.id)

            if issue is None and submission.status not in [STATUS_ACCEPTED, STATUS_PUBLISHED]:
                raise ValidationError(
                    {
                        "detail": (
                            f"Submission #{submission.id} must be 'accepted' or 'published'. "
                            f"Current status: {submission.status}."
                        )
                    }
                )

            if (
                issue is not None
                and not is_existing_article
                and submission.status not in [STATUS_ACCEPTED, STATUS_PUBLISHED]
            ):
                raise ValidationError(
                    {
                        "detail": (
                            f"Submission #{submission.id} must be 'accepted' or 'published' "
                            f"to add into this issue. "
                            f"Current status: {submission.status}."
                        )
                    }
                )

            if submission.issue_id and not is_existing_article:
                raise ValidationError(
                    {
                        "detail": (
                            f"Submission #{submission.id} is already assigned to issue #{submission.issue_id}."
                        )
                    }
                )

            if not submission.manuscript_pdf:
                raise ValidationError({"detail": f"Submission #{submission.id} has no manuscript PDF."})

            resolved_items.append((payload, submission))

        return resolved_items

    def _generate_issue_title(self, payload):
        title = (payload.get("title") or "").strip()
        if title:
            return title
        return (
            f"Volume {payload['volume']}, Issue {payload['issue_number']} "
            f"({payload['publication_year']})"
        )

    def _create_or_update_issue(self, issue, payload):
        resolved_items = self._resolve_submissions_for_issue(issue, payload["articles"])
        ordered_submissions = [submission for _, submission in resolved_items]
        merged_pdf_bytes = merge_submission_pdfs(ordered_submissions)
        issue_title = self._generate_issue_title(payload)

        if issue is None:
            if JournalIssue.objects.filter(
                volume=payload["volume"],
                issue_number=payload["issue_number"],
                publication_year=payload["publication_year"],
            ).exists():
                raise ValidationError(
                    {"detail": "This volume/issue/year combination already exists."}
                )
            issue = JournalIssue(
                title=issue_title,
                volume=payload["volume"],
                issue_number=payload["issue_number"],
                publication_year=payload["publication_year"],
                publication_date=payload.get("publication_date"),
            )
        else:
            duplicate_exists = JournalIssue.objects.filter(
                volume=payload["volume"],
                issue_number=payload["issue_number"],
                publication_year=payload["publication_year"],
            ).exclude(id=issue.id).exists()
            if duplicate_exists:
                raise ValidationError(
                    {"detail": "Another issue already exists with this volume/issue/year."}
                )
            issue.title = issue_title
            issue.volume = payload["volume"]
            issue.issue_number = payload["issue_number"]
            issue.publication_year = payload["publication_year"]
            issue.publication_date = payload.get("publication_date")

        pdf_name = (
            f"volume_{payload['volume']}_issue_{payload['issue_number']}_"
            f"{payload['publication_year']}.pdf"
        )

        with transaction.atomic():
            issue.full_issue_pdf.save(pdf_name, ContentFile(merged_pdf_bytes), save=False)
            issue.save()

            selected_ids = [submission.id for _, submission in resolved_items]
            Submission.objects.filter(issue=issue).exclude(id__in=selected_ids).update(
                issue=None,
                issue_order=None,
                page_start=None,
                page_end=None,
            )

            cursor = 1
            for article_payload, submission in resolved_items:
                page_count = get_submission_pdf_page_count(submission)
                page_start = cursor
                page_end = cursor + page_count - 1

                submission.issue = issue
                submission.issue_order = article_payload["order"]
                submission.page_start = page_start
                submission.page_end = page_end
                submission.status = STATUS_PUBLISHED
                ensure_local_doi(submission, save=False)
                submission.save(
                    update_fields=[
                        "issue",
                        "issue_order",
                        "page_start",
                        "page_end",
                        "status",
                        "doi",
                        "doi_status",
                        "updated_at",
                    ]
                )
                cursor = page_end + 1

        return issue

    def create(self, request, *args, **kwargs):
        """Create and publish a new issue + merged PDF."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        issue = self._create_or_update_issue(issue=None, payload=serializer.validated_data)
        try:
            from notifications.tasks import send_issue_author_journal_certificate_emails

            send_issue_author_journal_certificate_emails.delay(issue.id)
        except Exception:
            logger.exception(
                "Failed to queue journal certificate email task for issue_id=%s",
                issue.id,
            )
        output = JournalIssueDetailSerializer(issue, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Edit existing issue metadata/articles and rebuild merged PDF."""
        issue = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_issue = self._create_or_update_issue(issue=issue, payload=serializer.validated_data)
        try:
            from notifications.tasks import send_issue_author_journal_certificate_emails

            send_issue_author_journal_certificate_emails.delay(updated_issue.id)
        except Exception:
            logger.exception(
                "Failed to queue journal certificate email task for issue_id=%s",
                updated_issue.id,
            )
        output = JournalIssueDetailSerializer(updated_issue, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


class ReviewerListView(generics.ListAPIView):
    """GET /api/editor/reviewers - List approved reviewers for assignment dropdown."""

    permission_classes = [IsApprovedEditor]
    serializer_class = ReviewerOptionSerializer

    def get_queryset(self):
        qs = User.objects.filter(
            reviewer_status=APPROVAL_APPROVED,
        )
        # Ensure roles contains 'reviewer' in JSONField
        return qs.filter(roles__contains=[ROLE_REVIEWER])

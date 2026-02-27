"""Editorial views."""
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsApprovedEditor
from reviews.models import ReviewAssignment, STATUS_INVITED
from submissions.models import (
    STATUS_ACCEPTED,
    STATUS_DECISION_PENDING,
    STATUS_DESK_REJECTED,
    STATUS_REJECTED,
    STATUS_REVISION_REQUIRED,
    STATUS_SCREENING,
    STATUS_UNDER_REVIEW,
    Submission,
    SubmissionVersion,
)
from submissions.transitions import validate_transition

from .serializers import (
    DecisionSerializer,
    DeskRejectSerializer,
    EditorialSubmissionSerializer,
    InviteReviewerSerializer,
)


def get_submission_queryset():
    """Submissions visible to editors (all non-draft)."""
    return Submission.objects.filter(status__ne="draft").select_related(
        "author", "topic_area"
    ).prefetch_related("supplementary_files", "review_assignments")


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
                submission.id, old_status, STATUS_DESK_REJECTED,
                submission.author.email, submission.author_id,
                idempotency_key=f"status_{submission.id}_{old_status}_{STATUS_DESK_REJECTED}",
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
        queue_reviewer_invited(assignment.id, invited_email, submission.title or "Untitled")

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
            submission.save(update_fields=["status"])
            from audit.services import log
            log(actor_user=request.user, action_type="publish", target_type="submission", target_id=submission.id, old_value={"status": old_status}, new_value={"status": STATUS_PUBLISHED})

            from notifications.services import queue_submission_published
            queue_submission_published(submission.id, submission.author.email, submission.author.id)

        serializer = self.get_serializer(submission)
        return Response(serializer.data)


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

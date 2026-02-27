"""Reviewer views."""
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsApprovedReviewer

from .models import STATUS_ACCEPTED, STATUS_DECLINED, STATUS_INVITED, STATUS_REVIEW_SUBMITTED, Review, ReviewAssignment
from .serializers import ReviewAssignmentSerializer, ReviewSerializer


class ReviewAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Reviewer assignment list and retrieve."""

    permission_classes = [IsAuthenticated, IsApprovedReviewer]
    serializer_class = ReviewAssignmentSerializer

    def get_queryset(self):
        user = self.request.user
        return (
            ReviewAssignment.objects
            .filter(reviewer=user)
            .select_related("submission", "submission_version")
        )

    def list(self, request, *args, **kwargs):
        """GET /api/reviewer/assignments - List my assignments."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """GET /api/reviewer/assignments/{id} - Get assignment detail."""
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        """POST /api/reviewer/assignments/{id}/accept - Accept invitation."""
        assignment = self.get_object()
        if assignment.status != STATUS_INVITED:
            return Response(
                {"detail": "Only invited assignments can be accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        assignment.status = STATUS_ACCEPTED
        assignment.responded_at = timezone.now()
        assignment.reviewer = request.user
        assignment.save(update_fields=["status", "responded_at", "reviewer"])
        from audit.services import log
        log(actor_user=request.user, action_type="reviewer_accepted", target_type="review_assignment", target_id=assignment.id, old_value={"status": STATUS_INVITED}, new_value={"status": STATUS_ACCEPTED})
        from editorial.utils import get_editor_emails
        from notifications.services import queue_reviewer_accepted
        editor_emails = get_editor_emails()
        if editor_emails:
            queue_reviewer_accepted(assignment.id, editor_emails, assignment.submission.title or "Untitled")
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="decline")
    def decline(self, request, pk=None):
        """POST /api/reviewer/assignments/{id}/decline - Decline invitation."""
        assignment = self.get_object()
        if assignment.status != STATUS_INVITED:
            return Response(
                {"detail": "Only invited assignments can be declined."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        assignment.status = STATUS_DECLINED
        assignment.responded_at = timezone.now()
        assignment.reviewer = request.user
        assignment.save(update_fields=["status", "responded_at", "reviewer"])
        from audit.services import log
        log(actor_user=request.user, action_type="reviewer_declined", target_type="review_assignment", target_id=assignment.id, old_value={"status": STATUS_INVITED}, new_value={"status": STATUS_DECLINED})
        from editorial.utils import get_editor_emails
        from notifications.services import queue_reviewer_declined
        editor_emails = get_editor_emails()
        if editor_emails:
            queue_reviewer_declined(assignment.id, editor_emails, assignment.submission.title or "Untitled")
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="submit-review")
    def submit_review(self, request, pk=None):
        """POST /api/reviewer/assignments/{id}/submit-review - Submit structured review."""
        assignment = self.get_object()
        if assignment.status != STATUS_ACCEPTED:
            return Response(
                {"detail": "Review can only be submitted for accepted assignments."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if hasattr(assignment, "review") and assignment.review:
            return Response(
                {"detail": "Review already submitted for this assignment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        Review.objects.create(
            assignment=assignment,
            **serializer.validated_data,
        )
        assignment.status = STATUS_REVIEW_SUBMITTED
        assignment.save(update_fields=["status"])
        from audit.services import log
        log(actor_user=request.user, action_type="review_submitted", target_type="review_assignment", target_id=assignment.id, new_value={"submission_id": assignment.submission_id})
        from editorial.utils import get_editor_emails
        from notifications.services import queue_review_submitted
        editor_emails = get_editor_emails()
        if editor_emails:
            queue_review_submitted(assignment.submission_id, editor_emails, assignment.submission.title or "Untitled")

        out_serializer = self.get_serializer(assignment)
        return Response(out_serializer.data)


class AcceptByTokenView(viewsets.ViewSet):
    """Accept review assignment by secure token (for email invite link)."""

    permission_classes = [IsAuthenticated, IsApprovedReviewer]

    def list(self, request):
        """GET /api/reviewer/accept-by-token/?token=xxx - Get assignment info by token."""
        token = request.query_params.get("token")
        if not token:
            return Response({"detail": "Token query parameter required."}, status=status.HTTP_400_BAD_REQUEST)
        assignment = ReviewAssignment.objects.filter(token=token).select_related("submission", "submission_version").first()
        if not assignment:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_404_NOT_FOUND)
        if assignment.status != STATUS_INVITED:
            return Response(
                {"detail": "This invitation has already been responded to."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ReviewAssignmentSerializer(assignment, context={"request": request})
        return Response(serializer.data)

    def create(self, request):
        """POST /api/reviewer/accept-by-token - Accept by token, linking to current user. Body: {token: "..."}."""
        token = request.data.get("token")
        if not token:
            return Response({"detail": "Token required in body."}, status=status.HTTP_400_BAD_REQUEST)

        assignment = ReviewAssignment.objects.filter(token=token).select_related("submission").first()
        if not assignment:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_404_NOT_FOUND)
        if assignment.status != STATUS_INVITED:
            return Response(
                {"detail": "This invitation has already been responded to."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.reviewer = request.user
        assignment.status = STATUS_ACCEPTED
        assignment.responded_at = timezone.now()
        assignment.save(update_fields=["reviewer", "status", "responded_at"])
        from audit.services import log
        log(actor_user=request.user, action_type="reviewer_accepted", target_type="review_assignment", target_id=assignment.id, old_value={"status": STATUS_INVITED}, new_value={"status": STATUS_ACCEPTED})
        from editorial.utils import get_editor_emails
        from notifications.services import queue_reviewer_accepted
        editor_emails = get_editor_emails()
        if editor_emails:
            queue_reviewer_accepted(assignment.id, editor_emails, assignment.submission.title or "Untitled")

        serializer = ReviewAssignmentSerializer(assignment, context={"request": request})
        return Response(serializer.data)

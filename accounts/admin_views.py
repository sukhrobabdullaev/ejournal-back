"""Admin API views for per-journal user role approvals."""
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from journals.models import (
    MEMBERSHIP_STATUS_APPROVED,
    MEMBERSHIP_STATUS_REJECTED,
    JournalMembership,
)

from .models import User


class _ApproveOrRejectMembershipView(APIView):
    """Base for the four approve/reject views below. Requires request.journal
    (attached by JournalContextMiddleware from the /api/j/<slug>/... prefix).
    """

    permission_classes = [IsAdminUser]
    role = None  # "reviewer" or "editor"
    target_status = None  # MEMBERSHIP_STATUS_APPROVED or MEMBERSHIP_STATUS_REJECTED
    action_type = None
    require_reason = False

    def post(self, request, user_id, **kwargs):
        journal = getattr(request, "journal", None)
        if journal is None:
            return Response({"detail": "Journal context is required."}, status=status.HTTP_404_NOT_FOUND)

        reason = ""
        if self.require_reason:
            reason = request.data.get("reason", "").strip()
            if not reason:
                return Response({"detail": "Reason is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        membership = JournalMembership.objects.filter(
            user=user, journal=journal, role=self.role
        ).first()
        if not membership:
            return Response(
                {"detail": f"User does not have {self.role} role for this journal."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership.status = self.target_status
        membership.save(update_fields=["status", "updated_at"])

        from audit.services import log
        log(
            actor_user=request.user,
            action_type=self.action_type,
            target_type="journal_membership",
            target_id=membership.id,
            new_value={"reason": reason} if reason else None,
        )

        if self.target_status == MEMBERSHIP_STATUS_APPROVED:
            from notifications.services import queue_editor_approved, queue_reviewer_approved
            if self.role == "reviewer":
                queue_reviewer_approved(user.email, user.id, journal_name=journal.name)
            else:
                queue_editor_approved(user.email, user.id, journal_name=journal.name)

        return Response({"role": self.role, "status": membership.status})


class ApproveReviewerView(_ApproveOrRejectMembershipView):
    """POST /api/j/{slug}/admin/users/{id}/approve-reviewer - Approve reviewer role."""

    role = "reviewer"
    target_status = MEMBERSHIP_STATUS_APPROVED
    action_type = "reviewer_approved"


class ApproveEditorView(_ApproveOrRejectMembershipView):
    """POST /api/j/{slug}/admin/users/{id}/approve-editor - Approve editor role."""

    role = "editor"
    target_status = MEMBERSHIP_STATUS_APPROVED
    action_type = "editor_approved"


class RejectReviewerView(_ApproveOrRejectMembershipView):
    """POST /api/j/{slug}/admin/users/{id}/reject-reviewer - Reject reviewer role (reason required)."""

    role = "reviewer"
    target_status = MEMBERSHIP_STATUS_REJECTED
    action_type = "reviewer_rejected"
    require_reason = True


class RejectEditorView(_ApproveOrRejectMembershipView):
    """POST /api/j/{slug}/admin/users/{id}/reject-editor - Reject editor role (reason required)."""

    role = "editor"
    target_status = MEMBERSHIP_STATUS_REJECTED
    action_type = "editor_rejected"
    require_reason = True

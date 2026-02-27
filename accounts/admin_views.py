"""Admin API views for user role approvals."""
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import APPROVAL_APPROVED, APPROVAL_REJECTED, User


class ApproveReviewerView(APIView):
    """POST /api/admin/users/{id}/approve-reviewer - Approve reviewer role."""

    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if "reviewer" not in (user.roles or []):
            return Response(
                {"detail": "User does not have reviewer role."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.reviewer_status = APPROVAL_APPROVED
        user.save(update_fields=["reviewer_status"])

        from audit.services import log
        log(actor_user=request.user, action_type="reviewer_approved", target_type="user", target_id=user_id)

        return Response({"reviewer_status": user.reviewer_status})


class ApproveEditorView(APIView):
    """POST /api/admin/users/{id}/approve-editor - Approve editor role."""

    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if "editor" not in (user.roles or []):
            return Response(
                {"detail": "User does not have editor role."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.editor_status = APPROVAL_APPROVED
        user.save(update_fields=["editor_status"])

        from audit.services import log
        log(actor_user=request.user, action_type="editor_approved", target_type="user", target_id=user_id)

        return Response({"editor_status": user.editor_status})


class RejectReviewerView(APIView):
    """POST /api/admin/users/{id}/reject-reviewer - Reject reviewer role (reason required)."""

    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response(
                {"detail": "Reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if "reviewer" not in (user.roles or []):
            return Response(
                {"detail": "User does not have reviewer role."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.reviewer_status = APPROVAL_REJECTED
        user.save(update_fields=["reviewer_status"])

        from audit.services import log
        log(
            actor_user=request.user,
            action_type="reviewer_rejected",
            target_type="user",
            target_id=user_id,
            new_value={"reason": reason},
        )

        return Response({"reviewer_status": user.reviewer_status})


class RejectEditorView(APIView):
    """POST /api/admin/users/{id}/reject-editor - Reject editor role (reason required)."""

    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response(
                {"detail": "Reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if "editor" not in (user.roles or []):
            return Response(
                {"detail": "User does not have editor role."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.editor_status = APPROVAL_REJECTED
        user.save(update_fields=["editor_status"])

        from audit.services import log
        log(
            actor_user=request.user,
            action_type="editor_rejected",
            target_type="user",
            target_id=user_id,
            new_value={"reason": reason},
        )

        return Response({"editor_status": user.editor_status})

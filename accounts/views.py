"""Account and auth views."""
from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.views import APIView

from .models import User
from .serializers import SignupSerializer, UserSerializer
from .tokens import generate_email_verification_token, verify_email_verification_token
from notifications.services import queue_email_verification, queue_profile_updated


class SignupView(generics.CreateAPIView):
    """POST /api/auth/signup - Create new user account."""

    permission_classes = [AllowAny]
    serializer_class = SignupSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token = generate_email_verification_token(user)
        frontend_url = getattr(settings, "FRONTEND_URL", request.build_absolute_uri("/")).rstrip("/")
        verification_url = f"{frontend_url}/verify-email?token={token}"
        queue_email_verification(user.id, user.email, verification_url)

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "roles": user.roles,
                "reviewer_status": user.reviewer_status,
                "editor_status": user.editor_status,
                "message": "Account created. Check your email to verify your address, then use /api/auth/login to obtain tokens.",
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """GET /api/me - Retrieve current user. PATCH /api/me - Update profile."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        user = self.request.user
        tracked_fields = ["full_name", "affiliation", "country", "orcid_id", "google_scholar_url"]
        before = {field: getattr(user, field, "") for field in tracked_fields}

        serializer.save()

        changed_fields = []
        for field in tracked_fields:
            old_value = (before.get(field) or "").strip() if isinstance(before.get(field), str) else before.get(field)
            new_raw = getattr(user, field, "")
            new_value = (new_raw or "").strip() if isinstance(new_raw, str) else new_raw
            if old_value != new_value:
                changed_fields.append(field)

        if changed_fields:
            queue_profile_updated(
                user_id=user.id,
                to_email=user.email,
                roles=user.roles or [],
                changed_fields=changed_fields,
            )


class VerifyEmailView(APIView):
    """Verify email address (supports GET with query or POST with body)."""

    permission_classes = [AllowAny]

    def _handle(self, token: str | None):
        if not token:
            return Response(
                {"detail": "Missing token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = verify_email_verification_token(token)
        if not user:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

        return Response(
            {
                "message": "Email verified successfully.",
                "email": user.email,
            },
            status=status.HTTP_200_OK,
        )

    def get(self, request, *args, **kwargs):
        """GET /api/auth/verify-email?token=..."""
        token = request.query_params.get("token")
        return self._handle(token)

    def post(self, request, *args, **kwargs):
        """POST /api/auth/verify-email with JSON body {\"token\": \"...\"}."""
        token = request.data.get("token")
        return self._handle(token)


class ResendVerificationEmailView(APIView):
    """POST /api/auth/resend-verification - resend verification email."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Do not reveal whether email exists
            return Response(
                {"message": "If an account exists for this email, a verification message has been sent."},
                status=status.HTTP_200_OK,
            )

        if user.is_email_verified:
            return Response(
                {"message": "Email is already verified."},
                status=status.HTTP_200_OK,
            )

        token = generate_email_verification_token(user)
        frontend_url = getattr(settings, "FRONTEND_URL", request.build_absolute_uri("/")).rstrip("/")
        verification_url = f"{frontend_url}/verify-email?token={token}"
        queue_email_verification(user.id, user.email, verification_url)

        return Response(
            {"message": "Verification email sent."},
            status=status.HTTP_200_OK,
        )


# Re-export JWT views for URL wiring
LoginView = TokenObtainPairView
RefreshView = TokenRefreshView

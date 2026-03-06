"""Account and auth views."""
from django.urls import reverse
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .serializers import SignupSerializer, UserSerializer
from .tokens import generate_email_verification_token, verify_email_verification_token
from notifications.services import queue_email_verification
from rest_framework.views import APIView


class SignupView(generics.CreateAPIView):
    """POST /api/auth/signup - Create new user account."""

    permission_classes = [AllowAny]
    serializer_class = SignupSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token = generate_email_verification_token(user)
        verify_path = reverse("auth-verify-email")
        verification_url = request.build_absolute_uri(f"{verify_path}?token={token}")
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


class VerifyEmailView(APIView):
    """GET /api/auth/verify-email?token=... - Verify email address."""

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        token = request.query_params.get("token")
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


# Re-export JWT views for URL wiring
LoginView = TokenObtainPairView
RefreshView = TokenRefreshView

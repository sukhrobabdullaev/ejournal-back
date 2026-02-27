"""Account and auth views."""
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import User
from .serializers import SignupSerializer, UserSerializer


class SignupView(generics.CreateAPIView):
    """POST /api/auth/signup - Create new user account."""

    permission_classes = [AllowAny]
    serializer_class = SignupSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "roles": user.roles,
                "reviewer_status": user.reviewer_status,
                "editor_status": user.editor_status,
                "message": "Account created. Use /api/auth/login to obtain tokens.",
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """GET /api/me - Retrieve current user. PATCH /api/me - Update profile."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


# Re-export JWT views for URL wiring
LoginView = TokenObtainPairView
RefreshView = TokenRefreshView

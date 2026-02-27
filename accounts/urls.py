"""Account and auth URL routes."""
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .jwt_serializers import CustomTokenObtainPairSerializer
from .views import MeView, SignupView


class CustomTokenObtainPairView(TokenObtainPairView):
    """Login view with custom token payload (user_id, roles)."""
    serializer_class = CustomTokenObtainPairSerializer


urlpatterns = [
    path("auth/signup", SignupView.as_view(), name="auth-signup"),
    path("auth/login", CustomTokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me", MeView.as_view(), name="me"),
]

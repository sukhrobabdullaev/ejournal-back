"""Integration views (file upload, etc.)."""
import uuid

from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from accounts.permissions import IsEmailVerified
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class UploadFileView(APIView):
    """POST /api/upload-file - Upload a file via form-data, get back its URL."""

    permission_classes = [IsAuthenticated, IsEmailVerified]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, **kwargs):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"detail": "Provide 'file' in form-data."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        filename = file_obj.name or "file"
        safe_name = f"{uuid.uuid4().hex}_{filename}"
        path = default_storage.save(f"uploads/{safe_name}", file_obj)
        url = request.build_absolute_uri(default_storage.url(path))
        return Response({"url": url}, status=status.HTTP_201_CREATED)

"""Integration views (ORCID, file upload, etc.)."""
import base64
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class UploadFileView(APIView):
    """POST /api/upload-file - Upload a file, get back its URL. Use form-data (file) or JSON (file_base64, filename)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if file_obj:
            filename = file_obj.name or "file"
            safe_name = f"{uuid.uuid4().hex}_{filename}"
            path = default_storage.save(f"uploads/{safe_name}", file_obj)
        else:
            file_base64 = request.data.get("file_base64")
            filename = request.data.get("filename", "file")
            if not file_base64:
                return Response(
                    {"detail": "Provide 'file' (form-data) or 'file_base64' + 'filename' (JSON)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                content = base64.b64decode(file_base64, validate=True)
            except Exception:
                return Response({"detail": "Invalid base64 encoding."}, status=status.HTTP_400_BAD_REQUEST)
            if not content:
                return Response({"detail": "Empty file content."}, status=status.HTTP_400_BAD_REQUEST)
            safe_name = f"{uuid.uuid4().hex}_{filename}"
            path = default_storage.save(f"uploads/{safe_name}", ContentFile(content))

        url = request.build_absolute_uri(default_storage.url(path))
        return Response({"url": url}, status=status.HTTP_201_CREATED)


class OrcidConnectView(APIView):
    """
    POST /api/orcid/connect - Stub for ORCID OAuth connection.
    When implemented: complete OAuth flow and store orcid_id on user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        orcid_id = request.data.get("orcid_id", "").strip()
        if not orcid_id:
            return Response(
                {"detail": "orcid_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Stub: store orcid_id directly; real impl would validate via OAuth
        request.user.orcid_id = orcid_id
        request.user.save(update_fields=["orcid_id"])
        return Response(
            {"orcid_id": request.user.orcid_id, "message": "ORCID connected (stub)."},
            status=status.HTTP_200_OK,
        )

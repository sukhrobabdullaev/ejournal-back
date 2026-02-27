"""Integration views (ORCID, etc.)."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


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

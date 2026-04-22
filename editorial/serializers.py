"""Editorial serializers."""
from django.db.models import ObjectDoesNotExist
from rest_framework import serializers

from accounts.models import User
from reviews.models import ReviewAssignment
from submissions.models import (
    JournalIssue,
    STATUS_ACCEPTED,
    Submission,
    STATUS_DESK_REJECTED,
    STATUS_PUBLISHED,
    STATUS_REJECTED,
)
from submissions.serializers import (
    JournalIssueSerializer,
    SubmissionSupplementaryFileSerializer,
    TopicAreaSerializer,
)


class EditorialSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for editorial submission list/detail."""

    topic_area = TopicAreaSerializer(read_only=True)
    issue = JournalIssueSerializer(read_only=True)
    supplementary_files = SubmissionSupplementaryFileSerializer(many=True, read_only=True)
    review_assignments = serializers.SerializerMethodField()
    reason = serializers.SerializerMethodField()
    author_orcid_id = serializers.SerializerMethodField()
    author_google_scholar_url = serializers.SerializerMethodField()
    author_has_orcid = serializers.SerializerMethodField()
    author_has_google_scholar = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id",
            "status",
            "doi",
            "doi_status",
            "reason",
            "title",
            "abstract",
            "keywords",
            "topic_area",
            "author",
            "author_orcid_id",
            "author_google_scholar_url",
            "author_has_orcid",
            "author_has_google_scholar",
            "desk_reject_reason",
            "editorial_decision",
            "decision_letter",
            "issue",
            "issue_order",
            "page_start",
            "page_end",
            "manuscript_pdf",
            "supplementary_files",
            "created_at",
            "updated_at",
            "review_assignments",
        ]

    def get_review_assignments(self, obj):
        result = []
        for a in obj.review_assignments.all():
            item = {
                "id": a.id,
                "reviewer": a.reviewer_id,
                "reviewer_email": a.reviewer.email if a.reviewer else a.invited_email,
                "status": a.status,
                "due_date": a.due_date,
                "invited_at": a.invited_at,
            }
            try:
                r = a.review
                item["review"] = {
                    "summary": r.summary,
                    "strengths": r.strengths,
                    "weaknesses": r.weaknesses,
                    "confidential_to_editor": r.confidential_to_editor,
                    "recommendation": r.recommendation,
                    "submitted_at": r.submitted_at,
                }
            except ObjectDoesNotExist:
                item["review"] = None
            result.append(item)
        return result

    def get_reason(self, obj):
        if obj.status == STATUS_DESK_REJECTED:
            return obj.desk_reject_reason or ""
        if obj.status == STATUS_REJECTED:
            return obj.decision_letter or ""
        return ""

    def get_author_orcid_id(self, obj):
        return (obj.author.orcid_id or "").strip()

    def get_author_google_scholar_url(self, obj):
        return (obj.author.google_scholar_url or "").strip()

    def get_author_has_orcid(self, obj):
        return bool((obj.author.orcid_id or "").strip())

    def get_author_has_google_scholar(self, obj):
        return bool((obj.author.google_scholar_url or "").strip())


class DeskRejectSerializer(serializers.Serializer):
    """Serializer for desk reject action."""

    reason = serializers.CharField(required=True, allow_blank=False)


class InviteReviewerSerializer(serializers.Serializer):
    """Serializer for invite reviewer action."""

    reviewer_user_id = serializers.IntegerField(required=False, allow_null=True)
    reviewer_email = serializers.EmailField(required=False, allow_blank=True)
    due_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        user_id = attrs.get("reviewer_user_id")
        email = attrs.get("reviewer_email", "").strip()
        if user_id and email:
            raise serializers.ValidationError("Provide either reviewer_user_id or reviewer_email, not both.")
        if not user_id and not email:
            raise serializers.ValidationError("Provide reviewer_user_id or reviewer_email.")
        return attrs


class DecisionSerializer(serializers.Serializer):
    """Serializer for editorial decision."""

    decision = serializers.ChoiceField(
        choices=["accept", "reject", "revision_required"],
        required=True,
    )
    decision_letter = serializers.CharField(required=True, allow_blank=False)


class ReviewerOptionSerializer(serializers.ModelSerializer):
    """Lightweight serializer for reviewer dropdown options."""

    is_approved_reviewer = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "affiliation",
            "country",
            "is_approved_reviewer",
        ]

    def get_is_approved_reviewer(self, obj):
        return obj.is_approved_reviewer()


class IssueArticleInputSerializer(serializers.Serializer):
    """Editor payload item for ordering accepted submissions inside an issue."""

    submission_id = serializers.IntegerField(required=True, min_value=1)
    order = serializers.IntegerField(required=True, min_value=1)
    page_start = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    page_end = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate(self, attrs):
        page_start = attrs.get("page_start")
        page_end = attrs.get("page_end")
        if page_start and page_end and page_end < page_start:
            raise serializers.ValidationError("page_end must be greater than or equal to page_start.")
        return attrs


class JournalIssueUpsertSerializer(serializers.Serializer):
    """Create/update payload for issue publishing + PDF merge."""

    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    volume = serializers.IntegerField(required=True, min_value=1)
    issue_number = serializers.IntegerField(required=True, min_value=1)
    publication_year = serializers.IntegerField(required=False, min_value=1900, max_value=3000)
    publication_date = serializers.DateField(required=False, allow_null=True)
    articles = IssueArticleInputSerializer(many=True, required=True, min_length=1)

    def validate(self, attrs):
        publication_date = attrs.get("publication_date")
        publication_year = attrs.get("publication_year")

        if publication_date:
            if publication_year and publication_year != publication_date.year:
                raise serializers.ValidationError(
                    "publication_year must match publication_date year."
                )
            attrs["publication_year"] = publication_date.year
        elif not publication_year:
            raise serializers.ValidationError(
                "Provide publication_year or publication_date."
            )

        return attrs

    def validate_articles(self, value):
        submission_ids = [item["submission_id"] for item in value]
        if len(submission_ids) != len(set(submission_ids)):
            raise serializers.ValidationError("Each submission can only be added once.")

        orders = [item["order"] for item in value]
        if len(orders) != len(set(orders)):
            raise serializers.ValidationError("Order values must be unique.")

        return value


class AcceptedSubmissionOptionSerializer(serializers.ModelSerializer):
    """Minimal accepted article serializer for Make Journal UI."""

    author_name = serializers.CharField(source="author.full_name", read_only=True)
    author_email = serializers.CharField(source="author.email", read_only=True)
    manuscript_pdf_url = serializers.SerializerMethodField()
    manuscript_page_count = serializers.SerializerMethodField()
    is_already_assigned = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id",
            "status",
            "title",
            "author_name",
            "author_email",
            "created_at",
            "updated_at",
            "manuscript_pdf_url",
            "manuscript_page_count",
            "is_already_assigned",
            "issue",
            "issue_order",
            "page_start",
            "page_end",
        ]

    def get_manuscript_pdf_url(self, obj):
        if not obj.manuscript_pdf:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.manuscript_pdf.url) if request else obj.manuscript_pdf.url

    def get_manuscript_page_count(self, obj):
        if not obj.manuscript_pdf:
            return None
        try:
            from PyPDF2 import PdfReader

            obj.manuscript_pdf.open("rb")
            reader = PdfReader(obj.manuscript_pdf)
            return len(reader.pages)
        except Exception:
            return None
        finally:
            try:
                obj.manuscript_pdf.close()
            except Exception:
                pass

    def get_is_already_assigned(self, obj):
        return bool(obj.issue_id)


class JournalIssueArticleSerializer(serializers.ModelSerializer):
    """Article rows displayed in issue TOC."""

    author_name = serializers.CharField(source="author.full_name", read_only=True)
    manuscript_pdf_url = serializers.SerializerMethodField()
    manuscript_page_count = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id",
            "title",
            "doi",
            "author_name",
            "issue_order",
            "page_start",
            "page_end",
            "manuscript_page_count",
            "status",
            "manuscript_pdf_url",
        ]

    def get_manuscript_pdf_url(self, obj):
        if not obj.manuscript_pdf:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.manuscript_pdf.url) if request else obj.manuscript_pdf.url

    def get_manuscript_page_count(self, obj):
        if not obj.manuscript_pdf:
            return None
        try:
            from PyPDF2 import PdfReader

            obj.manuscript_pdf.open("rb")
            reader = PdfReader(obj.manuscript_pdf)
            return len(reader.pages)
        except Exception:
            return None
        finally:
            try:
                obj.manuscript_pdf.close()
            except Exception:
                pass


class JournalIssueDetailSerializer(serializers.ModelSerializer):
    """Issue serializer with table of contents."""

    full_issue_pdf_url = serializers.SerializerMethodField()
    articles = serializers.SerializerMethodField()

    class Meta:
        model = JournalIssue
        fields = [
            "id",
            "title",
            "volume",
            "issue_number",
            "publication_year",
            "publication_date",
            "full_issue_pdf_url",
            "created_at",
            "updated_at",
            "articles",
        ]

    def get_full_issue_pdf_url(self, obj):
        if not obj.full_issue_pdf:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.full_issue_pdf.url) if request else obj.full_issue_pdf.url

    def get_articles(self, obj):
        queryset = (
            obj.articles
            .select_related("author")
            .filter(status__in=[STATUS_ACCEPTED, STATUS_PUBLISHED])
            .order_by("issue_order", "id")
        )
        serializer = JournalIssueArticleSerializer(
            queryset,
            many=True,
            context=self.context,
        )
        return serializer.data

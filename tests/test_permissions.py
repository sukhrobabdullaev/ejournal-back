"""Tests for permission classes."""
from django.test import RequestFactory, TestCase
from rest_framework.test import force_authenticate

from accounts.models import User
from accounts.permissions import IsApprovedEditor, IsApprovedReviewer, IsAuthor
from journals.models import MEMBERSHIP_STATUS_APPROVED
from tests.helpers import make_journal, make_membership

_email_counter = [0]


def make_user(roles, reviewer_status=None, editor_status=None, is_email_verified=True, journal=None):
    """Create a test user with given roles and approval status, scoped to `journal`."""
    _email_counter[0] += 1
    user = User.objects.create_user(
        email=f"user_{_email_counter[0]}@test.com",
        password="testpass123",
        full_name="Test User",
        is_email_verified=is_email_verified,
    )
    for role in roles:
        status = MEMBERSHIP_STATUS_APPROVED
        if role == "reviewer" and reviewer_status is not None:
            status = reviewer_status
        if role == "editor" and editor_status is not None:
            status = editor_status
        make_membership(user, journal, role, status=status)
    return user


def make_request(factory, journal, user=None):
    request = factory.get("/")
    request.journal = journal
    if user is not None:
        force_authenticate(request, user=user)
    return request


class IsAuthorPermissionTest(TestCase):
    """Test IsAuthor permission."""

    def setUp(self):
        self.factory = RequestFactory()
        self.permission = IsAuthor()
        self.journal = make_journal()

    def test_anonymous_denied(self):
        request = make_request(self.factory, self.journal)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_author_allowed(self):
        user = make_user(["author"], is_email_verified=True, journal=self.journal)
        request = make_request(self.factory, self.journal, user=user)
        self.assertTrue(self.permission.has_permission(request, None))

    def test_author_unverified_denied(self):
        user = make_user(["author"], is_email_verified=False, journal=self.journal)
        request = make_request(self.factory, self.journal, user=user)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_reviewer_only_denied(self):
        user = make_user(["reviewer"], reviewer_status=MEMBERSHIP_STATUS_APPROVED, journal=self.journal)
        request = make_request(self.factory, self.journal, user=user)
        self.assertFalse(self.permission.has_permission(request, None))


class IsApprovedReviewerPermissionTest(TestCase):
    """Test IsApprovedReviewer permission."""

    def setUp(self):
        self.factory = RequestFactory()
        self.permission = IsApprovedReviewer()
        self.journal = make_journal()

    def test_anonymous_denied(self):
        request = make_request(self.factory, self.journal)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_reviewer_pending_denied(self):
        user = make_user(["reviewer"], reviewer_status="pending", journal=self.journal)
        request = make_request(self.factory, self.journal, user=user)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_reviewer_approved_allowed(self):
        user = make_user(
            ["reviewer"], reviewer_status=MEMBERSHIP_STATUS_APPROVED, is_email_verified=True, journal=self.journal
        )
        request = make_request(self.factory, self.journal, user=user)
        self.assertTrue(self.permission.has_permission(request, None))

    def test_reviewer_approved_unverified_denied(self):
        user = make_user(
            ["reviewer"], reviewer_status=MEMBERSHIP_STATUS_APPROVED, is_email_verified=False, journal=self.journal
        )
        request = make_request(self.factory, self.journal, user=user)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_author_only_denied(self):
        user = make_user(["author"], journal=self.journal)
        request = make_request(self.factory, self.journal, user=user)
        self.assertFalse(self.permission.has_permission(request, None))


class IsApprovedEditorPermissionTest(TestCase):
    """Test IsApprovedEditor permission."""

    def setUp(self):
        self.factory = RequestFactory()
        self.permission = IsApprovedEditor()
        self.journal = make_journal()

    def test_anonymous_denied(self):
        request = make_request(self.factory, self.journal)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_editor_pending_denied(self):
        user = make_user(["editor"], editor_status="pending", journal=self.journal)
        request = make_request(self.factory, self.journal, user=user)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_editor_approved_allowed(self):
        user = make_user(
            ["editor"], editor_status=MEMBERSHIP_STATUS_APPROVED, is_email_verified=True, journal=self.journal
        )
        request = make_request(self.factory, self.journal, user=user)
        self.assertTrue(self.permission.has_permission(request, None))

    def test_editor_approved_unverified_denied(self):
        user = make_user(
            ["editor"], editor_status=MEMBERSHIP_STATUS_APPROVED, is_email_verified=False, journal=self.journal
        )
        request = make_request(self.factory, self.journal, user=user)
        self.assertFalse(self.permission.has_permission(request, None))

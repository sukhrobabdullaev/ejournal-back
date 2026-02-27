"""Tests for permission classes."""
from django.test import RequestFactory, TestCase
from rest_framework.test import force_authenticate

from accounts.models import APPROVAL_APPROVED, User
from accounts.permissions import IsApprovedEditor, IsApprovedReviewer, IsAuthor


def make_user(roles, reviewer_status=None, editor_status=None):
    """Create a test user with given roles and approval status."""
    user = User.objects.create_user(
        email=f"user_{roles}@test.com",
        password="testpass123",
        full_name="Test User",
        roles=roles,
    )
    if reviewer_status is not None:
        user.reviewer_status = reviewer_status
    if editor_status is not None:
        user.editor_status = editor_status
    user.save()
    return user


class IsAuthorPermissionTest(TestCase):
    """Test IsAuthor permission."""

    def setUp(self):
        self.factory = RequestFactory()
        self.permission = IsAuthor()

    def test_anonymous_denied(self):
        request = self.factory.get("/")
        self.assertFalse(self.permission.has_permission(request, None))

    def test_author_allowed(self):
        user = make_user(["author"])
        request = self.factory.get("/")
        force_authenticate(request, user=user)
        self.assertTrue(self.permission.has_permission(request, None))

    def test_reviewer_only_denied(self):
        user = make_user(["reviewer"], reviewer_status=APPROVAL_APPROVED)
        request = self.factory.get("/")
        force_authenticate(request, user=user)
        self.assertFalse(self.permission.has_permission(request, None))


class IsApprovedReviewerPermissionTest(TestCase):
    """Test IsApprovedReviewer permission."""

    def setUp(self):
        self.factory = RequestFactory()
        self.permission = IsApprovedReviewer()

    def test_anonymous_denied(self):
        request = self.factory.get("/")
        self.assertFalse(self.permission.has_permission(request, None))

    def test_reviewer_pending_denied(self):
        user = make_user(["reviewer"], reviewer_status="pending")
        request = self.factory.get("/")
        force_authenticate(request, user=user)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_reviewer_approved_allowed(self):
        user = make_user(["reviewer"], reviewer_status=APPROVAL_APPROVED)
        request = self.factory.get("/")
        force_authenticate(request, user=user)
        self.assertTrue(self.permission.has_permission(request, None))

    def test_author_only_denied(self):
        user = make_user(["author"])
        request = self.factory.get("/")
        force_authenticate(request, user=user)
        self.assertFalse(self.permission.has_permission(request, None))


class IsApprovedEditorPermissionTest(TestCase):
    """Test IsApprovedEditor permission."""

    def setUp(self):
        self.factory = RequestFactory()
        self.permission = IsApprovedEditor()

    def test_anonymous_denied(self):
        request = self.factory.get("/")
        self.assertFalse(self.permission.has_permission(request, None))

    def test_editor_pending_denied(self):
        user = make_user(["editor"], editor_status="pending")
        request = self.factory.get("/")
        force_authenticate(request, user=user)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_editor_approved_allowed(self):
        user = make_user(["editor"], editor_status=APPROVAL_APPROVED)
        request = self.factory.get("/")
        force_authenticate(request, user=user)
        self.assertTrue(self.permission.has_permission(request, None))

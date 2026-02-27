"""Tests for submission status transitions."""
from django.test import TestCase

from submissions.transitions import can_transition, validate_transition


class SubmissionTransitionsTest(TestCase):
    """Test valid and invalid status transitions."""

    def test_draft_to_submitted_allowed(self):
        self.assertTrue(can_transition("draft", "submitted"))

    def test_draft_to_screening_not_allowed(self):
        self.assertFalse(can_transition("draft", "screening"))

    def test_submitted_to_screening_allowed(self):
        self.assertTrue(can_transition("submitted", "screening"))

    def test_screening_to_desk_rejected_allowed(self):
        self.assertTrue(can_transition("screening", "desk_rejected"))

    def test_screening_to_under_review_allowed(self):
        self.assertTrue(can_transition("screening", "under_review"))

    def test_under_review_to_decision_pending_allowed(self):
        self.assertTrue(can_transition("under_review", "decision_pending"))

    def test_decision_pending_to_accepted_allowed(self):
        self.assertTrue(can_transition("decision_pending", "accepted"))

    def test_decision_pending_to_rejected_allowed(self):
        self.assertTrue(can_transition("decision_pending", "rejected"))

    def test_decision_pending_to_revision_required_allowed(self):
        self.assertTrue(can_transition("decision_pending", "revision_required"))

    def test_accepted_to_published_allowed(self):
        self.assertTrue(can_transition("accepted", "published"))

    def test_final_states_have_no_outgoing(self):
        for final in ("desk_rejected", "rejected", "published", "withdrawn"):
            self.assertEqual(can_transition(final, "submitted"), False)
            self.assertEqual(can_transition(final, "draft"), False)

    def test_validate_transition_raises_on_invalid(self):
        with self.assertRaises(ValueError) as ctx:
            validate_transition("draft", "screening")
        self.assertIn("Invalid status transition", str(ctx.exception))
        self.assertIn("draft", str(ctx.exception))
        self.assertIn("screening", str(ctx.exception))

    def test_validate_transition_succeeds_on_valid(self):
        validate_transition("draft", "submitted")  # No exception

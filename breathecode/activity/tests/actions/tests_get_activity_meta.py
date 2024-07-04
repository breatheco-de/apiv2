"""
Test /answer
"""

from unittest.mock import MagicMock, call, patch

from django.utils import timezone
from faker import Faker
from task_manager.core.exceptions import AbortTask

from breathecode.activity.actions import FillActivityMeta, get_activity_meta

from ..mixins import MediaTestCase

UTC_NOW = timezone.now()

fake = Faker()


def obj():
    return {
        fake.slug(): fake.slug(),
        fake.slug(): fake.slug(),
        fake.slug(): fake.slug(),
    }


ALLOWED_TYPES = [
    ("auth.UserInvite", "user_invite", "invite_created", obj()),
    ("auth.UserInvite", "user_invite", "invite_status_updated", obj()),
    ("feedback.Answer", "answer", "nps_answered", obj()),
    ("auth.User", "user", "login", obj()),
    ("assignments.Task", "task", "open_syllabus_module", obj()),
    ("assignments.Task", "task", "read_assignment", obj()),
    ("assignments.Task", "task", "assignment_review_status_updated", obj()),
    ("assignments.Task", "task", "assignment_status_updated", obj()),
    ("events.EventCheckin", "event_checkin", "event_checkin_created", obj()),
    ("events.EventCheckin", "event_checkin", "event_checkin_assisted", obj()),
    ("payments.Bag", "bag", "bag_created", obj()),
    ("payments.Subscription", "subscription", "checkout_completed", obj()),
    ("payments.PlanFinancing", "plan_financing", "checkout_completed", obj()),
    ("mentorship.MentorshipSession", "mentorship_session", "mentoring_session_scheduled", obj()),
    ("mentorship.MentorshipSession", "mentorship_session", "mentorship_session_checkin", obj()),
    ("mentorship.MentorshipSession", "mentorship_session", "mentorship_session_checkout", obj()),
]


class MediaTestSuite(MediaTestCase):

    def test_just_kind(self):
        kind = self.bc.fake.slug()

        meta = get_activity_meta(kind)
        expected = {}

        self.assertEqual(meta, expected)

    def test_type_and_no_id_or_slug(self):
        kind = self.bc.fake.slug()

        with self.assertRaisesMessage(AbortTask, "related_id or related_slug must be present"):
            get_activity_meta(kind, related_type="auth.User")

    def test_bad_related_type(self):
        related_type = self.bc.fake.slug()
        kind = self.bc.fake.slug()

        with self.assertRaisesMessage(AbortTask, f"{related_type} is not supported yet"):
            get_activity_meta(kind, related_type=related_type, related_id=1)

    def test_kind_not_sopported_by_related_type(self):
        related_type = self.bc.fake.slug()
        kind = self.bc.fake.slug()

        allowed = [
            "auth.UserInvite",
            "feedback.Answer",
            "auth.User",
            "assignments.Task",
            "events.EventCheckin",
            "payments.Bag",
            "payments.Subscription",
            "payments.PlanFinancing",
            "mentorship.MentorshipSession",
        ]

        for related_type in allowed:
            with self.assertRaisesMessage(AbortTask, f"kind {kind} is not supported by {related_type}"):
                get_activity_meta(kind, related_type=related_type, related_id=1)

    def test_kind_sopported_by_related_type(self):
        kind = self.bc.fake.slug()

        for path, func, kind, obj in ALLOWED_TYPES:
            with patch.object(FillActivityMeta, func, MagicMock(return_value=obj)) as mock:
                meta = get_activity_meta(kind, related_type=path, related_id=1)

                self.bc.check.calls(mock.call_args_list, [call(kind, 1, None)])
                self.assertEqual(meta, obj)

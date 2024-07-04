from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from django.utils import timezone

from breathecode.payments.tasks import refund_mentoring_session
from breathecode.tests.mixins.legacy import LegacyAPITestCase


class TestLead(LegacyAPITestCase):
    """
    🔽🔽🔽 With status PENDING
    """

    @patch("breathecode.feedback.tasks.send_mentorship_session_survey.delay", MagicMock())
    @patch("breathecode.payments.tasks.refund_mentoring_session.delay", MagicMock())
    def test_mentorship_session_status__with_status_pending(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {"status": "PENDING"}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=1)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])
        self.assertEqual(refund_mentoring_session.delay.call_args_list, [])

    """
    🔽🔽🔽 With status STARTED
    """

    @patch("breathecode.feedback.tasks.send_mentorship_session_survey.delay", MagicMock())
    @patch("breathecode.payments.tasks.refund_mentoring_session.delay", MagicMock())
    def test_mentorship_session_status__with_status_started(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {"status": "STARTED"}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=1)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])
        self.assertEqual(refund_mentoring_session.delay.call_args_list, [])

    """
    🔽🔽🔽 With status FAILED
    """

    @patch("breathecode.feedback.tasks.send_mentorship_session_survey.delay", MagicMock())
    @patch("breathecode.payments.tasks.refund_mentoring_session.delay", MagicMock())
    def test_mentorship_session_status__with_status_failed(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {"status": "FAILED"}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=1)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])
        self.assertEqual(refund_mentoring_session.delay.call_args_list, [])

    @patch("breathecode.feedback.tasks.send_mentorship_session_survey.delay", MagicMock())
    @patch("breathecode.payments.tasks.refund_mentoring_session.delay", MagicMock())
    def test_mentorship_session_status__with_status_failed__with_mentor_and_mentee(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {"status": "FAILED"}
        model = self.bc.database.create(
            mentorship_session=mentorship_session, mentorship_service=1, mentor_profile=1, user=1
        )

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])
        self.assertEqual(refund_mentoring_session.delay.call_args_list, [call(1)])

    """
    🔽🔽🔽 With status IGNORED
    """

    @patch("breathecode.feedback.tasks.send_mentorship_session_survey.delay", MagicMock())
    @patch("breathecode.payments.tasks.refund_mentoring_session.delay", MagicMock())
    def test_mentorship_session_status__with_status_ignored(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {"status": "IGNORED"}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=1)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])
        self.assertEqual(refund_mentoring_session.delay.call_args_list, [])

    @patch("breathecode.feedback.tasks.send_mentorship_session_survey.delay", MagicMock())
    @patch("breathecode.payments.tasks.refund_mentoring_session.delay", MagicMock())
    def test_mentorship_session_status__with_status_ignored__with_mentor_and_mentee(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {"status": "IGNORED"}
        model = self.bc.database.create(
            mentorship_session=mentorship_session, mentorship_service=1, mentor_profile=1, user=1
        )

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])
        self.assertEqual(refund_mentoring_session.delay.call_args_list, [call(1)])

    """
    🔽🔽🔽 With status COMPLETED and duration 0:00:00 because it not have started_at and ended_at
    """

    @patch("breathecode.feedback.tasks.send_mentorship_session_survey.delay", MagicMock())
    @patch("breathecode.payments.tasks.refund_mentoring_session.delay", MagicMock())
    def test_mentorship_session_status__with_status_completed__duration_equal_to_zero(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {"status": "COMPLETED"}
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=1)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])
        self.assertEqual(refund_mentoring_session.delay.call_args_list, [])

    """
    🔽🔽🔽 With status COMPLETED and duration 0:05:00
    """

    @patch("breathecode.feedback.tasks.send_mentorship_session_survey.delay", MagicMock())
    @patch("breathecode.payments.tasks.refund_mentoring_session.delay", MagicMock())
    def test_mentorship_session_status__with_status_completed__duration_equal_to_five_minutes(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import send_mentorship_session_survey

        utc_now = timezone.now()
        mentorship_session = {
            "status": "COMPLETED",
            "started_at": utc_now,
            "ended_at": utc_now + timedelta(minutes=5),
        }
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=1)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])
        self.assertEqual(refund_mentoring_session.delay.call_args_list, [])

    """
    🔽🔽🔽 With status COMPLETED and duration greater than 0:05:00 but without mentee and mentor
    """

    @patch("breathecode.feedback.tasks.send_mentorship_session_survey.delay", MagicMock())
    @patch("breathecode.payments.tasks.refund_mentoring_session.delay", MagicMock())
    def test_mentorship_session_status__with_status_completed__duration_greater_than_five_minutes(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import send_mentorship_session_survey

        utc_now = timezone.now()
        mentorship_session = {
            "status": "COMPLETED",
            "started_at": utc_now,
            "ended_at": utc_now + timedelta(minutes=5, seconds=1),
        }
        model = self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=1)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])
        self.assertEqual(refund_mentoring_session.delay.call_args_list, [])

    """
    🔽🔽🔽 With status COMPLETED, duration greater than 0:05:00, with mentee and with mentor
    """

    @patch("breathecode.feedback.tasks.send_mentorship_session_survey.delay", MagicMock())
    @patch("breathecode.payments.tasks.refund_mentoring_session.delay", MagicMock())
    def test_mentorship_session_status__with_status_completed__with_mentee__with_mentor(self, enable_signals):
        enable_signals()

        from breathecode.feedback.tasks import send_mentorship_session_survey

        utc_now = timezone.now()
        mentorship_session = {
            "status": "COMPLETED",
            "started_at": utc_now,
            "ended_at": utc_now + timedelta(minutes=5, seconds=1),
        }
        model = self.bc.database.create(mentorship_session=mentorship_session, user=1, mentorship_service=1)

        self.assertEqual(
            self.bc.database.list_of("mentorship.MentorshipSession"),
            [
                self.bc.format.to_dict(model.mentorship_session),
            ],
        )

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [call(1)])
        self.assertEqual(refund_mentoring_session.delay.call_args_list, [])

        # """
        # 🔽🔽🔽 With status COMPLETED, duration greater than 0:05:00, with mentee and with mentor, with service
        # """

        # @patch('breathecode.feedback.tasks.send_mentorship_session_survey.delay', MagicMock())
        # @patch('breathecode.payments.tasks.refund_mentoring_session.delay', MagicMock())
        # def test_mentorship_session_status__with_status_completed__with_mentee__with_mentor_and_service(self, enable_signals):
        enable_signals()

    #     from breathecode.feedback.tasks import send_mentorship_session_survey

    #     utc_now = timezone.now()
    #     mentorship_session = {
    #         'status': 'COMPLETED',
    #         'started_at': utc_now,
    #         'ended_at': utc_now + timedelta(minutes=5, seconds=1),
    #     }
    #     model = self.bc.database.create(mentorship_session=mentorship_session, user=1, mentorship_service=1)

    #     self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
    #         self.bc.format.to_dict(model.mentorship_session),
    #     ])

    #     self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [call(1)])
    #     self.assertEqual(refund_mentoring_session.delay.call_args_list, [])

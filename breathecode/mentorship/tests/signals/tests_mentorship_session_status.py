from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from rest_framework import status
from django.utils import timezone
from ..mixins import MentorshipTestCase


class LeadTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 With status PENDING
    """

    @patch('breathecode.feedback.tasks.send_mentorship_session_survey.delay', MagicMock())
    def test_mentorship_session_status__with_status_pending(self):
        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {'status': 'PENDING'}
        model = self.bc.database.create(mentorship_session=mentorship_session)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])

    """
    🔽🔽🔽 With status STARTED
    """

    @patch('breathecode.feedback.tasks.send_mentorship_session_survey.delay', MagicMock())
    def test_mentorship_session_status__with_status_started(self):
        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {'status': 'STARTED'}
        model = self.bc.database.create(mentorship_session=mentorship_session)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])

    """
    🔽🔽🔽 With status FAILED
    """

    @patch('breathecode.feedback.tasks.send_mentorship_session_survey.delay', MagicMock())
    def test_mentorship_session_status__with_status_failed(self):
        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {'status': 'FAILED'}
        model = self.bc.database.create(mentorship_session=mentorship_session)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])

    """
    🔽🔽🔽 With status IGNORED
    """

    @patch('breathecode.feedback.tasks.send_mentorship_session_survey.delay', MagicMock())
    def test_mentorship_session_status__with_status_ignored(self):
        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {'status': 'IGNORED'}
        model = self.bc.database.create(mentorship_session=mentorship_session)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])

    """
    🔽🔽🔽 With status COMPLETED and duration 0:00:00 because it not have started_at and ended_at
    """

    @patch('breathecode.feedback.tasks.send_mentorship_session_survey.delay', MagicMock())
    def test_mentorship_session_status__with_status_completed__duration_equal_to_zero(self):
        from breathecode.feedback.tasks import send_mentorship_session_survey

        mentorship_session = {'status': 'COMPLETED'}
        model = self.bc.database.create(mentorship_session=mentorship_session)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])

    """
    🔽🔽🔽 With status COMPLETED and duration 0:05:00
    """

    @patch('breathecode.feedback.tasks.send_mentorship_session_survey.delay', MagicMock())
    def test_mentorship_session_status__with_status_completed__duration_equal_to_five_minutes(self):
        from breathecode.feedback.tasks import send_mentorship_session_survey

        utc_now = timezone.now()
        mentorship_session = {
            'status': 'COMPLETED',
            'started_at': utc_now,
            'ended_at': utc_now + timedelta(minutes=5),
        }
        model = self.bc.database.create(mentorship_session=mentorship_session)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])

    """
    🔽🔽🔽 With status COMPLETED and duration greater than 0:05:00 but without mentee and mentor
    """

    @patch('breathecode.feedback.tasks.send_mentorship_session_survey.delay', MagicMock())
    def test_mentorship_session_status__with_status_completed__duration_greater_than_five_minutes(self):
        from breathecode.feedback.tasks import send_mentorship_session_survey

        utc_now = timezone.now()
        mentorship_session = {
            'status': 'COMPLETED',
            'started_at': utc_now,
            'ended_at': utc_now + timedelta(minutes=5, seconds=1),
        }
        model = self.bc.database.create(mentorship_session=mentorship_session)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [])

    """
    🔽🔽🔽 With status COMPLETED, duration greater than 0:05:00, with mentee and with mentor
    """

    @patch('breathecode.feedback.tasks.send_mentorship_session_survey.delay', MagicMock())
    def test_mentorship_session_status__with_status_completed__with_mentee__with_mentor(self):
        from breathecode.feedback.tasks import send_mentorship_session_survey

        utc_now = timezone.now()
        mentorship_session = {
            'status': 'COMPLETED',
            'started_at': utc_now,
            'ended_at': utc_now + timedelta(minutes=5, seconds=1),
        }
        model = self.bc.database.create(mentorship_session=mentorship_session, user=1)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])

        self.assertEqual(send_mentorship_session_survey.delay.call_args_list, [call(1)])

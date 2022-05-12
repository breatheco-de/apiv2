"""
Test mentorhips
"""
import random, datetime
from unittest.mock import patch
from django.db.models.query import QuerySet
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from breathecode.tests.mocks.requests import REQUESTS_PATH, apply_requests_request_mock

from breathecode.authenticate.models import Token
from ..mixins import MentorshipTestCase
from ...models import MentorshipSession
from ...actions import get_pending_sessions_or_create, generate_mentor_bills

NOW = timezone.now()


class GenerateMentorBillsTestCase(MentorshipTestCase):
    @patch('django.utils.timezone.now', MagicMock(return_value=NOW))
    def test_generate_bills_with_no_previous_bills_no_unpaid_sessions(self):
        """
        First bill generate, with no previous bills.
        """

        models = self.bc.database.create(mentor_profile=1, user=1, mentorship_session=1)
        mentor = models.mentor_profile

        bills = generate_mentor_bills(mentor)

        self.assertEqual(len(bills), 0)

    @patch('django.utils.timezone.now', MagicMock(return_value=NOW))
    def test_generate_bills_with_no_previous_bills_pending_sessions(self):
        """
        Generate bills with no previous billing history and 3 previous sessions
        """

        models_a = self.bc.database.create(mentor_profile=1,
                                           user=1,
                                           mentorship_session={
                                               'status': 'COMPLETED',
                                               'started_at': NOW - datetime.timedelta(days=80, hours=2),
                                               'ended_at': NOW - datetime.timedelta(days=80, hours=1),
                                               'accounted_duration': datetime.timedelta(hours=1)
                                           })
        models = self.bc.database.create(mentor_profile=1,
                                         user=1,
                                         mentorship_session=[{
                                             'status':
                                             'COMPLETED',
                                             'started_at':
                                             NOW - datetime.timedelta(days=80, hours=2),
                                             'ended_at':
                                             NOW - datetime.timedelta(days=80, hours=1),
                                             'accounted_duration':
                                             datetime.timedelta(hours=1)
                                         }, {
                                             'status':
                                             'COMPLETED',
                                             'started_at':
                                             NOW - datetime.timedelta(days=79, hours=3),
                                             'ended_at':
                                             NOW - datetime.timedelta(days=79, hours=1),
                                             'accounted_duration':
                                             datetime.timedelta(hours=2)
                                         }, {
                                             'status':
                                             'COMPLETED',
                                             'started_at':
                                             NOW - datetime.timedelta(days=40, hours=3),
                                             'ended_at':
                                             NOW - datetime.timedelta(days=40, hours=1),
                                             'accounted_duration':
                                             datetime.timedelta(hours=2)
                                         }])
        mentor = models.mentor_profile

        bills = generate_mentor_bills(mentor)

        self.assertEqual(len(bills), 4)
        self.assertEqual(bills[0].total_duration_in_hours, 3)

    @patch('django.utils.timezone.now', MagicMock(return_value=NOW))
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_generate_bills_with_previous_bills_and_pending_sessions(self):
        """
        Generate bills with no previous billing history and 3 previous sessions
        """
        start = NOW - datetime.timedelta(days=80, hours=2)
        end = NOW - datetime.timedelta(days=80, hours=1)
        start_month = start.replace(day=28, hour=23, minute=59, second=59)
        end_month = start.replace(day=28, hour=23, minute=59, second=59) + datetime.timedelta(days=4)
        models_a = self.bc.database.create(mentor_profile=1,
                                           user=1,
                                           mentorship_session={
                                               'status': 'COMPLETED',
                                               'started_at': start,
                                               'ended_at': end,
                                               'accounted_duration': datetime.timedelta(hours=1)
                                           },
                                           mentorship_bill={
                                               'started_at': start_month,
                                               'ended_at': end_month
                                           })
        models = self.bc.database.create(mentor_profile=models_a['mentor_profile'],
                                         user=models_a['user'],
                                         mentorship_session=[{
                                             'status':
                                             'COMPLETED',
                                             'started_at':
                                             NOW - datetime.timedelta(days=49, hours=2),
                                             'ended_at':
                                             NOW - datetime.timedelta(days=49, hours=1),
                                             'accounted_duration':
                                             datetime.timedelta(hours=1)
                                         }, {
                                             'status':
                                             'COMPLETED',
                                             'started_at':
                                             NOW - datetime.timedelta(days=48, hours=3),
                                             'ended_at':
                                             NOW - datetime.timedelta(days=48, hours=1),
                                             'accounted_duration':
                                             datetime.timedelta(hours=2)
                                         }, {
                                             'status':
                                             'COMPLETED',
                                             'started_at':
                                             NOW - datetime.timedelta(days=5, hours=3),
                                             'ended_at':
                                             NOW - datetime.timedelta(days=5, hours=1),
                                             'accounted_duration':
                                             datetime.timedelta(hours=2)
                                         }])
        mentor = models.mentor_profile

        bills = generate_mentor_bills(mentor)

        # first generated bill needs to be one month after the previous one
        self.assertEqual(bills[0].started_at.month, start.month + 1)
        self.assertEqual(len(bills), 3)

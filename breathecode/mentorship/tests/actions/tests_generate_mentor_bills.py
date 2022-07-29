"""
Test mentorships
"""
import datetime
from unittest.mock import patch
from unittest.mock import MagicMock, patch

import pytz

from ..mixins import MentorshipTestCase
from ...actions import generate_mentor_bills

NOW = datetime.datetime(year=2022, month=1, day=5, hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC)


def mentorship_bill_field(data={}):
    return {
        'academy_id': 0,
        'ended_at': None,
        'id': 0,
        'mentor_id': 0,
        'overtime_minutes': 0.0,
        'paid_at': None,
        'reviewer_id': None,
        'started_at': None,
        'status': 'DUE',
        'status_mesage': None,
        'total_duration_in_hours': 0.0,
        'total_duration_in_minutes': 0.0,
        'total_price': 0.0,
        **data,
    }


#FIXME: improve this tests
class GenerateMentorBillsTestCase(MentorshipTestCase):

    @patch('django.utils.timezone.now', MagicMock(return_value=NOW))
    def test_generate_bills_with_no_previous_bills_no_unpaid_sessions(self):
        """
        First bill generate, with no previous bills.
        """

        models = self.bc.database.create(mentor_profile=1, user=1, mentorship_session=1)
        mentor = models.mentor_profile

        bills = generate_mentor_bills(mentor)

        #FIXME
        self.assertEqual(len(bills), 0)

    @patch('django.utils.timezone.now', MagicMock(return_value=NOW))
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
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

        list_bills = [self.bc.format.to_dict(x) for x in bills]

        bill1 = round((models.mentorship_session[0].accounted_duration.seconds +
                       models.mentorship_session[1].accounted_duration.seconds) / 60 / 60,
                      2) * models.mentor_profile.price_per_hour

        bill2 = round((models.mentorship_session[2].accounted_duration.seconds) / 60 / 60,
                      2) * models.mentor_profile.price_per_hour

        self.assertEqual(
            list_bills, [
                mentorship_bill_field(
                    {
                        'academy_id': 2,
                        'ended_at': datetime.datetime(2021, 10, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        'id': 1,
                        'mentor_id': 2,
                        'overtime_minutes': 60.0,
                        'started_at': datetime.datetime(2021, 10, 16, 22, 0, tzinfo=pytz.UTC),
                        'total_duration_in_hours': 3.0,
                        'total_duration_in_minutes': 180.0,
                        'total_price': bill1,
                    }),
                mentorship_bill_field(
                    {
                        'academy_id': 2,
                        'ended_at': datetime.datetime(2021, 11, 30, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        'id': 2,
                        'mentor_id': 2,
                        'overtime_minutes': 60.0,
                        'started_at': datetime.datetime(2021, 11, 1, 0, 0, 0, 999999, tzinfo=pytz.UTC),
                        'total_duration_in_hours': 2.0,
                        'total_duration_in_minutes': 120.0,
                        'total_price': bill2,
                    }),
                mentorship_bill_field(
                    {
                        'academy_id': 2,
                        'ended_at': datetime.datetime(2021, 12, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        'id': 3,
                        'mentor_id': 2,
                        'overtime_minutes': 0.0,
                        'started_at': datetime.datetime(2021, 12, 1, 0, 0, 0, 999999, tzinfo=pytz.UTC),
                        'total_duration_in_hours': 0.0,
                        'total_duration_in_minutes': 0,
                        'total_price': 0.0,
                    }),
                mentorship_bill_field(
                    {
                        'academy_id': 2,
                        'ended_at': datetime.datetime(2022, 1, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        'id': 4,
                        'mentor_id': 2,
                        'overtime_minutes': 0.0,
                        'started_at': datetime.datetime(2022, 1, 1, 0, 0, 0, 999999, tzinfo=pytz.UTC),
                        'total_duration_in_hours': 0.0,
                        'total_duration_in_minutes': 0,
                        'total_price': 0.0,
                    }),
            ])
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
        list_bills = [self.bc.format.to_dict(x) for x in bills]

        bill1 = round((models.mentorship_session[0].accounted_duration.seconds +
                       models.mentorship_session[1].accounted_duration.seconds) / 60 / 60,
                      2) * models.mentor_profile.price_per_hour

        bill2 = round((models.mentorship_session[2].accounted_duration.seconds) / 60 / 60,
                      2) * models.mentor_profile.price_per_hour

        self.assertEqual(
            list_bills, [
                mentorship_bill_field(
                    {
                        'academy_id': 1,
                        'ended_at': datetime.datetime(2021, 11, 30, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        'id': 2,
                        'mentor_id': 1,
                        'overtime_minutes': 60.0,
                        'started_at': datetime.datetime(2021, 11, 2, 0, 0, tzinfo=pytz.UTC),
                        'total_duration_in_hours': 3.0,
                        'total_duration_in_minutes': 180.0,
                        'total_price': bill1,
                    }),
                mentorship_bill_field(
                    {
                        'academy_id': 1,
                        'ended_at': datetime.datetime(2021, 12, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        'id': 3,
                        'mentor_id': 1,
                        'overtime_minutes': 60.0,
                        'started_at': datetime.datetime(2021, 12, 1, 0, 0, 0, 999999, tzinfo=pytz.UTC),
                        'total_duration_in_hours': 2.0,
                        'total_duration_in_minutes': 120.0,
                        'total_price': bill2,
                    }),
                mentorship_bill_field(
                    {
                        'academy_id': 1,
                        'ended_at': datetime.datetime(2022, 1, 31, 23, 59, 59, 999999, tzinfo=pytz.UTC),
                        'id': 4,
                        'mentor_id': 1,
                        'overtime_minutes': 0.0,
                        'started_at': datetime.datetime(2022, 1, 1, 0, 0, 0, 999999, tzinfo=pytz.UTC),
                        'total_duration_in_hours': 0.0,
                        'total_duration_in_minutes': 0,
                        'total_price': 0.0,
                    }),
            ])
        # first generated bill needs to be one month after the previous one
        self.assertEqual(bills[0].started_at.month, start.month + 1)

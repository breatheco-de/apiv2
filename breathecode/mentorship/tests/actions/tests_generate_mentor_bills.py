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


def mentorship_session_field(data={}):
    return {
        'name': None,
        'is_online': False,
        'latitude': None,
        'longitude': None,
        'mentor_id': 0,
        'service_id': None,
        'mentee_id': None,
        'online_meeting_url': None,
        'online_recording_url': None,
        'status': 'PENDING',
        'status_message': None,
        'allow_billing': True,
        'bill_id': None,
        'accounted_duration': None,
        'agenda': None,
        'summary': None,
        'starts_at': None,
        'ends_at': None,
        'started_at': None,
        'ended_at': None,
        'mentor_joined_at': None,
        'mentor_left_at': None,
        'mentee_left_at': None,
        'suggested_accounted_duration': None,
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

        self.assertEqual(bills, [])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [])
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(models.mentorship_session),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=NOW))
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_generate_bills_with_no_previous_bills_pending_sessions(self):
        """
        Generate bills with no previous billing history and 3 previous sessions
        """

        models_a = self.bc.database.create(mentor_profile=1,
                                           user=1,
                                           mentorship_service=1,
                                           mentorship_session={
                                               'status': 'COMPLETED',
                                               'started_at': NOW - datetime.timedelta(days=80, hours=2),
                                               'ended_at': NOW - datetime.timedelta(days=80, hours=1),
                                               'accounted_duration': datetime.timedelta(hours=1)
                                           })
        models = self.bc.database.create(mentor_profile=1,
                                         user=1,
                                         mentorship_service=1,
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
        first = sorted(models.mentorship_session, key=lambda x: x.started_at)[0].started_at
        latest = sorted(models.mentorship_session, key=lambda x: x.ended_at, reverse=True)[0].ended_at

        bill = round((models.mentorship_session[0].accounted_duration.seconds +
                      models.mentorship_session[1].accounted_duration.seconds +
                      models.mentorship_session[2].accounted_duration.seconds) / 60 / 60,
                     2) * models.mentor_profile.price_per_hour

        self.assertEqual(list_bills, [
            mentorship_bill_field({
                'academy_id': 2,
                'ended_at': latest,
                'id': 1,
                'mentor_id': 2,
                'overtime_minutes': 120.0,
                'started_at': first,
                'total_duration_in_hours': 5.0,
                'total_duration_in_minutes': 300.0,
                'total_price': bill,
            }),
        ])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            mentorship_bill_field({
                'academy_id': 2,
                'ended_at': latest,
                'id': 1,
                'mentor_id': 2,
                'overtime_minutes': 120.0,
                'started_at': first,
                'total_duration_in_hours': 5.0,
                'total_duration_in_minutes': 300.0,
                'total_price': bill,
            }),
        ])

        status_message = ('The mentor never joined the meeting, no time will be '
                          'accounted for.')

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            mentorship_session_field({
                'accounted_duration': datetime.timedelta(seconds=3600),
                'id': 1,
                'mentee_id': 1,
                'mentor_id': 1,
                'service_id': 1,
                'status': 'COMPLETED',
                'started_at': NOW - datetime.timedelta(days=80, hours=2),
                'ended_at': NOW - datetime.timedelta(days=80, hours=1),
                'bill_id': None,
            }),
            mentorship_session_field({
                'accounted_duration': datetime.timedelta(seconds=3600),
                'id': 2,
                'mentee_id': 2,
                'mentor_id': 2,
                'service_id': 2,
                'status': 'COMPLETED',
                'status_message': status_message,
                'suggested_accounted_duration': datetime.timedelta(0),
                'started_at': NOW - datetime.timedelta(days=80, hours=2),
                'ended_at': NOW - datetime.timedelta(days=80, hours=1),
                'summary': None,
                'bill_id': 1,
            }),
            mentorship_session_field({
                'accounted_duration': datetime.timedelta(seconds=7200),
                'id': 3,
                'mentee_id': 2,
                'mentor_id': 2,
                'service_id': 2,
                'status': 'COMPLETED',
                'status_message': status_message,
                'suggested_accounted_duration': datetime.timedelta(0),
                'started_at': NOW - datetime.timedelta(days=79, hours=3),
                'ended_at': NOW - datetime.timedelta(days=79, hours=1),
                'summary': None,
                'bill_id': 1,
            }),
            mentorship_session_field({
                'accounted_duration': datetime.timedelta(seconds=7200),
                'id': 4,
                'mentee_id': 2,
                'mentor_id': 2,
                'service_id': 2,
                'status': 'COMPLETED',
                'status_message': status_message,
                'suggested_accounted_duration': datetime.timedelta(0),
                'started_at': NOW - datetime.timedelta(days=40, hours=3),
                'ended_at': NOW - datetime.timedelta(days=40, hours=1),
                'summary': None,
                'bill_id': 1,
            }),
        ])

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
                                           mentorship_service=1,
                                           mentorship_bill={
                                               'started_at': start_month,
                                               'ended_at': end_month
                                           })
        models = self.bc.database.create(mentor_profile=models_a['mentor_profile'],
                                         user=models_a['user'],
                                         mentorship_service=1,
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

        bill = round((models_a.mentorship_session.accounted_duration.seconds +
                      models.mentorship_session[0].accounted_duration.seconds +
                      models.mentorship_session[1].accounted_duration.seconds +
                      models.mentorship_session[2].accounted_duration.seconds) / 60 / 60,
                     2) * models.mentor_profile.price_per_hour

        self.assertEqual(list_bills, [
            mentorship_bill_field({
                'academy_id': 1,
                'ended_at': NOW - datetime.timedelta(days=5, hours=1),
                'id': 2,
                'mentor_id': 1,
                'overtime_minutes': 120.0,
                'started_at': NOW - datetime.timedelta(days=80, hours=2),
                'total_duration_in_hours': 6.0,
                'total_duration_in_minutes': 360.0,
                'total_price': bill,
            }),
        ])
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            mentorship_bill_field({
                'academy_id': 1,
                'ended_at': NOW - datetime.timedelta(days=5, hours=1),
                'id': 2,
                'mentor_id': 1,
                'overtime_minutes': 120.0,
                'started_at': NOW - datetime.timedelta(days=80, hours=2),
                'total_duration_in_hours': 6.0,
                'total_duration_in_minutes': 360.0,
                'total_price': bill,
            }),
        ])

        status_message = ('The mentor never joined the meeting, no time will be '
                          'accounted for.')

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            mentorship_session_field({
                'accounted_duration': datetime.timedelta(seconds=3600),
                'id': 1,
                'mentee_id': 1,
                'mentor_id': 1,
                'service_id': 1,
                'status': 'COMPLETED',
                'status_message': status_message,
                'suggested_accounted_duration': datetime.timedelta(0),
                'started_at': start,
                'ended_at': end,
                'summary': None,
                'bill_id': 2,
            }),
            mentorship_session_field({
                'accounted_duration': datetime.timedelta(seconds=3600),
                'id': 2,
                'mentee_id': 1,
                'mentor_id': 1,
                'service_id': 2,
                'status': 'COMPLETED',
                'status_message': status_message,
                'suggested_accounted_duration': datetime.timedelta(0),
                'started_at': NOW - datetime.timedelta(days=49, hours=2),
                'ended_at': NOW - datetime.timedelta(days=49, hours=1),
                'summary': None,
                'bill_id': 2,
            }),
            mentorship_session_field({
                'accounted_duration': datetime.timedelta(seconds=7200),
                'id': 3,
                'mentee_id': 1,
                'mentor_id': 1,
                'service_id': 2,
                'status': 'COMPLETED',
                'status_message': status_message,
                'suggested_accounted_duration': datetime.timedelta(0),
                'started_at': NOW - datetime.timedelta(days=48, hours=3),
                'ended_at': NOW - datetime.timedelta(days=48, hours=1),
                'summary': None,
                'bill_id': 2,
            }),
            mentorship_session_field({
                'accounted_duration': datetime.timedelta(seconds=7200),
                'id': 4,
                'mentee_id': 1,
                'mentor_id': 1,
                'service_id': 2,
                'status': 'COMPLETED',
                'status_message': status_message,
                'suggested_accounted_duration': datetime.timedelta(0),
                'started_at': NOW - datetime.timedelta(days=5, hours=3),
                'ended_at': NOW - datetime.timedelta(days=5, hours=1),
                'summary': None,
                'bill_id': 2,
            }),
        ])

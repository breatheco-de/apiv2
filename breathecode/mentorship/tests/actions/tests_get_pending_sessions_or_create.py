"""
Test mentorhips
"""
import random
from unittest.mock import patch
from django.db.models.query import QuerySet
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from breathecode.tests.mocks.requests import REQUESTS_PATH, apply_requests_request_mock

from breathecode.authenticate.models import Token
from ... import actions
from ..mixins import MentorshipTestCase
from ...models import MentorshipSession
from ...actions import get_pending_sessions_or_create

daily_url = '/v1/rooms'
daily_payload = {'url': 'https://4geeks.daily.com/asdasd', 'name': 'asdasd'}

ENDS_AT = timezone.now()


def format_mentorship_session_attrs(attrs={}):
    return {
        'accounted_duration': None,
        'agenda': None,
        'allow_billing': True,
        'bill_id': None,
        'ended_at': None,
        'ends_at': None,
        'id': 0,
        'is_online': False,
        'latitude': None,
        'longitude': None,
        'mentee_id': None,
        'mentee_left_at': None,
        'mentor_id': 0,
        'mentor_joined_at': None,
        'mentor_left_at': None,
        'name': None,
        'online_meeting_url': None,
        'online_recording_url': None,
        'started_at': None,
        'starts_at': None,
        'status': 'PENDING',
        'status_message': None,
        'suggested_accounted_duration': None,
        'summary': None,
        **attrs,
    }


class GetOrCreateSessionTestSuite(MentorshipTestCase):
    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=ENDS_AT))
    @patch('breathecode.mentorship.actions.close_older_sessions', MagicMock())
    def test_create_session_mentor_first_no_previous_nothing(self):
        """
        When the mentor gets into the room before the mentee
        if should create a room with status 'pending'
        """

        models = self.bc.database.create(mentor_profile=1, user=1)

        mentor = models.mentor_profile
        mentor_token, created = Token.get_or_create(mentor.user, token_type='permanent')

        pending_sessions = get_pending_sessions_or_create(mentor_token, mentor, mentee=None)

        self.bc.check.queryset_of(pending_sessions, MentorshipSession)
        self.bc.check.queryset_with_pks(pending_sessions, [1])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            format_mentorship_session_attrs({
                'id': 1,
                'status': 'PENDING',
                'mentor_id': 1,
                'mentee_id': None,
                'is_online': True,
                'name': 'asdasd',
                'online_meeting_url': 'https://4geeks.daily.com/asdasd',
                'ends_at': ENDS_AT + timedelta(seconds=3600),
            }),
        ])

        self.assertEqual(actions.close_older_sessions.call_args_list, [call()])

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=ENDS_AT))
    @patch('breathecode.mentorship.actions.close_older_sessions', MagicMock())
    def test_create_session_mentor_first_previous_pending_without_mentee(self):
        """
        When the mentor gets into the room before the mentee but there was a previous unfinished without mentee
        it should re-use that previous room
        """

        mentorship_session = {'mentee_id': None}
        models = self.bc.database.create(mentor_profile=1, mentorship_session=mentorship_session)
        mentor = models.mentor_profile

        mentor_token, created = Token.get_or_create(mentor.user, token_type='permanent')

        # since there is a previous session without mentee, it should re use it
        pending_sessions = get_pending_sessions_or_create(mentor_token, mentor, mentee=None)

        self.bc.check.queryset_of(pending_sessions, MentorshipSession)
        self.bc.check.queryset_with_pks(pending_sessions, [1])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            format_mentorship_session_attrs({
                'id': 1,
                'status': 'PENDING',
                'mentor_id': 1,
                'mentee_id': None,
                'is_online': False,
                'ends_at': None,
            }),
        ])

        self.assertEqual(actions.close_older_sessions.call_args_list, [call()])

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=ENDS_AT))
    @patch('breathecode.mentorship.actions.close_older_sessions', MagicMock())
    def test_create_session_mentor_first_previous_pending_with_mentee(self):
        """
        Mentor comes first, there is a previous non-started session with a mentee,
        it should return that previouse one (because it needs to be closed) instead of creating a new one
        """

        mentorship_session = {'status': 'PENDING'}
        models = self.bc.database.create(mentor_profile=1, user=1, mentorship_session=mentorship_session)

        mentor = models.mentor_profile
        session = models.mentorship_session

        mentor_token, created = Token.get_or_create(mentor.user, token_type='permanent')
        sessions = get_pending_sessions_or_create(mentor_token, mentor)

        self.bc.check.queryset_of(sessions, MentorshipSession)
        self.bc.check.queryset_with_pks(sessions, [1])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            format_mentorship_session_attrs({
                'id': 1,
                'status': 'PENDING',
                'mentor_id': 1,
                'mentee_id': 1,
                'is_online': False,
                'ends_at': None,
            }),
        ])

        self.assertEqual(actions.close_older_sessions.call_args_list, [call()])

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=ENDS_AT))
    @patch('breathecode.mentorship.actions.close_older_sessions', MagicMock())
    #TODO: without mentee or with mentee?
    def test_create_session_mentor_first_started_without_mentee(self):
        """
        Mentor comes first, there is a previous started session with a mentee,
        it should return that previouse one (because it needs to be closed) instead of creating a new one
        """

        mentorship_session = {'status': 'STARTED', 'started_at': timezone.now(), 'mentee_id': None}
        models = self.bc.database.create(mentor_profile=1, user=1, mentorship_session=mentorship_session)
        mentor = models.mentor_profile

        mentor_token, created = Token.get_or_create(mentor.user, token_type='permanent')
        sessions = get_pending_sessions_or_create(mentor_token, mentor)

        self.bc.check.queryset_of(sessions, MentorshipSession)
        self.bc.check.queryset_with_pks(sessions, [1])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            format_mentorship_session_attrs({
                'id': 1,
                'status': 'STARTED',
                'mentor_id': 1,
                'mentee_id': None,
                'is_online': False,
                'ends_at': None,
                'started_at': ENDS_AT,
            }),
        ])

        self.assertEqual(actions.close_older_sessions.call_args_list, [call()])

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=ENDS_AT))
    @patch('breathecode.mentorship.actions.close_older_sessions', MagicMock())
    def test_create_session_mentee_first_no_previous_nothing(self):
        """
        Mentee comes first, there is nothing previously created
        it should return a brand new sessions with started at already started
        """

        models = self.bc.database.create(mentor_profile=1, user=2)
        mentor = models.mentor_profile
        mentee = models.user[1]

        mentee_token, created = Token.get_or_create(mentee, token_type='permanent')
        sessions = get_pending_sessions_or_create(mentee_token, mentor, mentee)

        self.bc.check.queryset_of(sessions, MentorshipSession)
        self.bc.check.queryset_with_pks(sessions, [1])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            format_mentorship_session_attrs({
                'id': 1,
                'status': 'PENDING',
                'mentor_id': 1,
                'mentee_id': 2,
                'is_online': True,
                'ends_at': ENDS_AT + timedelta(seconds=3600),
                'name': 'asdasd',
                'online_meeting_url': 'https://4geeks.daily.com/asdasd',
            }),
        ])

        self.assertEqual(actions.close_older_sessions.call_args_list, [call()])

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=ENDS_AT))
    @patch('breathecode.mentorship.actions.close_older_sessions', MagicMock())
    def test_create_session_mentee_first_with_wihout_mentee(self):
        """
        Mentee comes first, there is nothing previously created
        it should reuse the previous pending session
        """

        mentorship_session = {'status': 'PENDING', 'mentee_id': None}
        models = self.bc.database.create(mentor_profile=1, user=2, mentorship_session=mentorship_session)
        new_mentee = models.user[1]

        mentee_token, created = Token.get_or_create(new_mentee, token_type='permanent')
        sessions = get_pending_sessions_or_create(mentee_token, models.mentor_profile, mentee=new_mentee)

        self.bc.check.queryset_of(sessions, MentorshipSession)
        self.bc.check.queryset_with_pks(sessions, [1])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            format_mentorship_session_attrs({
                'id': 1,
                'status': 'PENDING',
                'mentor_id': 1,
                'mentee_id': None,
                'is_online': False,
            }),
        ])

        self.assertEqual(actions.close_older_sessions.call_args_list, [call()])

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=ENDS_AT))
    @patch('breathecode.mentorship.actions.close_older_sessions', MagicMock())
    def test_create_session_mentee_first_with_another_mentee(self):
        """
        Mentee comes first, there is a previous pending meeting with another mentee
        it should keep and ignore old one (untouched) and create and return new one for this mentee
        """

        # other random mentoring session precreated just for better testing

        mentorship_session = {'status': 'PENDING'}
        self.bc.database.create(mentor_profile=1, user=1, mentorship_session=mentorship_session)

        models = self.bc.database.create(mentor_profile=1, user=1, mentorship_session=mentorship_session)
        new_mentee = self.bc.database.create(user=1).user

        mentee_token, created = Token.get_or_create(new_mentee, token_type='permanent')
        sessions_to_render = get_pending_sessions_or_create(mentee_token,
                                                            models.mentor_profile,
                                                            mentee=new_mentee)

        self.bc.check.queryset_of(sessions_to_render, MentorshipSession)
        self.bc.check.queryset_with_pks(sessions_to_render, [3])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            format_mentorship_session_attrs({
                'id': 1,
                'ends_at': None,
                'mentee_id': 1,
                'mentor_id': 1,
            }),
            format_mentorship_session_attrs({
                'id': 2,
                'ends_at': None,
                'mentee_id': 2,
                'mentor_id': 2,
            }),
            format_mentorship_session_attrs({
                'id': 3,
                'status': 'PENDING',
                'mentor_id': 2,
                'mentee_id': 3,
                'is_online': True,
                'ends_at': ENDS_AT + timedelta(seconds=3600),
                'name': 'asdasd',
                'online_meeting_url': 'https://4geeks.daily.com/asdasd',
            }),
        ])

        self.assertEqual(actions.close_older_sessions.call_args_list, [call()])

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=ENDS_AT))
    @patch('breathecode.mentorship.actions.close_older_sessions', MagicMock())
    def test_create_session_mentee_first_with_another_same_mentee(self):
        """
        Mentee comes second, there is a previous pending meeting with same mentee
        it should keep and ignore old one (untouched) and create and return new one for this mentee
        """

        # some old meeting with another mentee, should be ignored
        self.bc.database.create(mentor_profile=1, user=1, mentorship_session={'status': 'PENDING'})

        # old meeting with SAME mentee, should be re-used
        models = self.bc.database.create(mentor_profile=1, user=1, mentorship_session={'status': 'PENDING'})
        same_mentee = models.user

        mentee_token, created = Token.get_or_create(same_mentee, token_type='permanent')
        sessions_to_render = get_pending_sessions_or_create(mentee_token,
                                                            models.mentor_profile,
                                                            mentee=same_mentee)

        self.bc.check.queryset_of(sessions_to_render, MentorshipSession)
        self.bc.check.queryset_with_pks(sessions_to_render, [2])

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            format_mentorship_session_attrs({
                'id': 1,
                'ends_at': None,
                'mentee_id': 1,
                'mentor_id': 1,
            }),
            format_mentorship_session_attrs({
                'id': 2,
                'status': 'PENDING',
                'mentor_id': 2,
                'mentee_id': 2,
                'is_online': False,
                'ends_at': None,
            }),
        ])

        self.assertEqual(actions.close_older_sessions.call_args_list, [call()])

"""
Test mentorhips
"""
import random
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from breathecode.tests.mocks.requests import REQUESTS_PATH, apply_requests_request_mock

from breathecode.authenticate.models import Token
from ..mixins import MentorshipTestCase
from ...models import MentorshipSession
from ...actions import get_pending_sessions_or_create

daily_url = '/v1/rooms'
daily_payload = {'url': 'https://4geeks.daily.com/asdasd', 'name': 'asdasd'}


class GetOrCreateSessionTestSuite(MentorshipTestCase):
    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    def test_create_session_mentor_first_no_previous_nothing(self):
        """
        When the mentor gets into the room before the mentee
        if should create a room with status 'pending'
        """

        models = self.bc.database.create(mentor=1, user=1)

        mentor = models.mentor
        mentor_token, created = Token.get_or_create(mentor.user, token_type='permanent')

        pending_sessions = get_pending_sessions_or_create(mentor_token, mentor, mentee=None)

        self.assertEqual(pending_sessions.count(), 1)
        session = pending_sessions.first()
        self.assertEqual(session.mentor.id, mentor.id)
        self.assertEqual(session.status, 'PENDING')
        self.assertEqual(session.mentee, None)

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    def test_create_session_mentor_first_previous_pending_without_mentee(self):
        """
        When the mentor gets into the room before the mentee but there was a previous unfinished without mentee
        it should re-use that previous room
        """

        models = self.bc.database.create(mentor=1)
        mentor = models.mentor
        mentor_token, created = Token.get_or_create(mentor.user, token_type='permanent')

        # let's set a previous pending empty session
        previous_session = self.bc.database.create(session=1, mentor=mentor).session

        # since there is a previous session without mentee, it should re use it
        pending_sessions = get_pending_sessions_or_create(mentor_token, mentor, mentee=None)

        self.assertEqual(pending_sessions.count(), 1)
        session = pending_sessions.first()
        self.assertEqual(session.mentor.id, mentor.id)
        self.assertEqual(session.id, previous_session.id)

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    def test_create_session_mentor_first_previous_pending_with_mentee(self):
        """
        Mentor comes first, there is a previous non-started session with a mentee,
        it should return that previouse one (because it needs to be closed) instead of creating a new one
        """

        models = self.bc.database.create(mentor=1, mentee=1, session={'status': 'PENDING'})
        mentor = models.mentor
        session = models.session

        mentor_token, created = Token.get_or_create(mentor.user, token_type='permanent')
        sessions = get_pending_sessions_or_create(mentor_token, mentor)

        self.assertEqual(session.status, 'PENDING')  #it should close the previous one as failed
        self.assertEqual(sessions.count(), 1)
        self.assertEqual(sessions.first().mentee.id, models.mentee.id)
        self.assertEqual(sessions.first().id, session.id)

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    def test_create_session_mentor_first_started_without_mentee(self):
        """
        Mentor comes first, there is a previous started session with a mentee,
        it should return that previouse one (because it needs to be closed) instead of creating a new one
        """

        models = self.bc.database.create(mentor=1,
                                         mentee=1,
                                         session={
                                             'status': 'STARTED',
                                             'started_at': timezone.now()
                                         })
        mentor = models.mentor
        session = models.session

        mentor_token, created = Token.get_or_create(mentor.user, token_type='permanent')
        sessions = get_pending_sessions_or_create(mentor_token, mentor)

        self.assertEqual(session.status, 'STARTED')  #it should close the previous one as failed
        self.assertEqual(sessions.count(), 1)
        self.assertEqual(sessions.first().mentee.id, models.mentee.id)
        self.assertEqual(sessions.first().id, session.id)

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    def test_create_session_mentee_first_no_previous_nothing(self):
        """
        Mentee comes first, there is nothing previously created
        it should returna brand new sessions with started at already started
        """

        models = self.bc.database.create(mentor=1, mentee=1)
        mentor = models.mentor
        mentee = models.mentee

        mentee_token, created = Token.get_or_create(mentee, token_type='permanent')
        sessions = get_pending_sessions_or_create(mentee_token, mentor, mentee)
        new_session = sessions.first()

        self.assertEqual(sessions.count(), 1)
        self.assertEqual(new_session.mentee.id, mentee_token.user.id)

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    def test_create_session_mentee_first_with_wihout_mentee(self):
        """
        Mentee comes first, there is nothing previously created
        it should reuse the previous pending session
        """

        new_mentee = self.bc.database.create(mentee=1).mentee
        models = self.bc.database.create(mentor=1, mentee=None, session={'status': 'PENDING'})

        mentee_token, created = Token.get_or_create(new_mentee, token_type='permanent')
        sessions = get_pending_sessions_or_create(mentee_token, models.mentor, mentee=new_mentee)

        self.assertEqual(sessions.count(), 1)
        self.assertEqual(models.session.id, sessions.first().id)

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    def test_create_session_mentee_first_with_another_mentee(self):
        """
        Mentee comes first, there is a previous pending meeting with another mentee
        it should keep and ignore old one (untouched) and create and return new one for this mentee
        """

        # other random mentoring session precreated just for better testing
        self.bc.database.create(mentor=1, mentee=1, session={'status': 'PENDING'})

        models = self.bc.database.create(mentor=1, mentee=1, session={'status': 'PENDING'})
        new_mentee = self.bc.database.create(mentee=1).mentee

        mentee_token, created = Token.get_or_create(new_mentee, token_type='permanent')
        sessions_to_render = get_pending_sessions_or_create(mentee_token, models.mentor, mentee=new_mentee)

        # two in total
        all_sessions = MentorshipSession.objects.all()
        self.assertEqual(all_sessions.count(), 3)

        # but one only to render becaue the mentee is asking
        self.assertEqual(sessions_to_render.count(), 1)
        self.assertNotEqual(models.session.id, sessions_to_render.first().id)

    @patch(REQUESTS_PATH['request'], apply_requests_request_mock([(200, daily_url, daily_payload)]))
    def test_create_session_mentee_first_with_another_same_mentee(self):
        """
        Mentee comes second, there is a previous pending meeting with same mentee
        it should keep and ignore old one (untouched) and create and return new one for this mentee
        """

        # some old meeting with another mentee, should be ignored
        self.bc.database.create(mentor=1, mentee=1, session={'status': 'PENDING'})

        # old meeting with SAME mentee, should be re-used
        models = self.bc.database.create(mentor=1, mentee=1, session={'status': 'PENDING'})
        same_mentee = models.mentee

        mentee_token, created = Token.get_or_create(same_mentee, token_type='permanent')
        sessions_to_render = get_pending_sessions_or_create(mentee_token, models.mentor, mentee=same_mentee)

        # two in total
        all_sessions = MentorshipSession.objects.all()
        self.assertEqual(all_sessions.count(), 2)

        # but one only to render because the mentee is checking in
        self.assertEqual(sessions_to_render.count(), 1)
        self.assertEqual(models.session.id, sessions_to_render.first().id)

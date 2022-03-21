"""
Test mentorhips
"""
import random
from unittest.mock import patch
from unittest.mock import MagicMock, call, patch
from breathecode.tests.mocks.requests import REQUESTS_PATH, apply_requests_request_mock

from breathecode.authenticate.models import Token
from ..mixins import MentorshipTestCase
from ...actions import get_pending_sessions_or_create


class GetOrCreateSessionTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Without Cohort
    """
    @patch(REQUESTS_PATH['request'],
           apply_requests_request_mock([
               (200, 'https://api.daily.co/v1/rooms', {
                   'url': 'https://4geeks.daily.com/asdasd',
                   'name': 'ASDFSDFG456DFVR'
               }),
           ]))
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

    @patch(REQUESTS_PATH['request'],
           apply_requests_request_mock([
               (200, 'https://api.daily.co/v1/rooms', {
                   'url': 'https://4geeks.daily.com/asdasd',
                   'name': 'ASDFSDFG456DFVR'
               }),
           ]))
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

    @patch(REQUESTS_PATH['request'],
           apply_requests_request_mock([
               (200, 'https://api.daily.co/v1/rooms', {
                   'url': 'https://4geeks.daily.com/asdasd',
                   'name': random.randrange(1, 10)
               }),
           ]))
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

    # @patch(REQUESTS_PATH['request'],
    #        apply_requests_request_mock([
    #            (200, 'https://api.daily.co/v1/rooms', {
    #                "url": "https://4geeks.daily.com/asdasd",
    #                "name": random.randrange(1, 10)
    #            }),
    #        ]))
    # def test_mentor_creating_session_previous_pending_same_mentee(self):
    #     """
    #     If there is a previous non-started pending session with the same mentee and mentor, it should re-use the room
    #     """

    #     mentee = self.bc.database.create(user=1).user
    #     models = self.bc.database.create(mentor=1, mentee=mentee, session={'status': 'PENDING'})
    #     mentor = models.mentor
    #     session = models.session

    #     mentor_token, created = Token.get_or_create(mentor.user, token_type='permanent')
    #     sessions = get_pending_sessions_or_create(mentor_token, mentor, mentee=mentee)

    #     self.assertEqual(sessions.count(), 1)
    #     self.assertEqual(sessions.first().mentee.id, session.mentee.id)
    #     self.assertEqual(sessions.first().id, session.id)

    # @patch(REQUESTS_PATH['request'],
    #        apply_requests_request_mock([
    #            (200, 'https://api.daily.co/v1/rooms', {
    #                "url": "https://4geeks.daily.com/asdasd",
    #                "name": random.randrange(1, 10)
    #            }),
    #        ]))
    # def test_create_session_previous_pending_same_mentee(self):
    #     """
    #     If there is a previous non-started sessions pending with the same mentee, it should re-use it
    #     """

    #     mentee = self.bc.database.create(user=1).user
    #     models = self.bc.database.create(mentor=1, mentee=mentee, session={'status': 'PENDING'})
    #     mentor = models.mentor
    #     session = models.session

    #     mentor_token, created = Token.get_or_create(mentor.user, token_type='permanent')
    #     sessions = get_pending_sessions_or_create(mentor_token, mentor, mentee=mentee)

    #     self.assertEqual(sessions.count(), 1)
    #     self.assertEqual(sessions.first().mentee.id, session.mentee.id)
    #     self.assertEqual(sessions.first().id, session.id)

    # @patch(REQUESTS_PATH['request'],
    #        apply_requests_request_mock([
    #            (200, 'https://api.daily.co/v1/rooms', {
    #                "url": "https://4geeks.daily.com/asdasd",
    #                "name": "ASDFSDFG456DFVR"
    #            }),
    #        ]))
    # def test_mentor_creating_session_previous_pending_other_mentee(self):
    #     """
    #     If there is a previous sessions pending with a different mentee, it should create a new one
    #     """

    #     other_mentee = self.bc.database.create(user=1).user
    #     models = self.bc.database.create(mentor=1, user=1, session={'status': 'PENDING'})
    #     mentor = models.mentor
    #     mentee = models.user
    #     session = models.session

    #     mentor_token, created = Token.get_or_create(mentor.user, token_type='permanent')
    #     sessions = get_pending_sessions_or_create(mentor_token, mentor, mentee=other_mentee)

    #     self.assertEqual(sessions.count(), 2)
    #     # self.assertEqual(sessions.first().id, session.id)

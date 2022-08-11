"""
Tasks tests
"""
from datetime import timedelta
from unittest.mock import MagicMock, patch, call
import breathecode.notify.actions as actions
from django.utils import timezone
from ..mixins import FeedbackTestCase
from ...utils import strings
from ...tasks import send_mentorship_session_survey

API_URL = 'http://kenny-was.reborn'
UTC_NOW = timezone.now()


def build_answer_dict(attrs={}):
    return {
        'academy_id': None,
        'cohort_id': None,
        'comment': None,
        'event_id': None,
        'highest': 'very likely',
        'id': 1,
        'lang': 'en',
        'lowest': 'not likely',
        'mentor_id': None,
        'mentorship_session_id': None,
        'opened_at': None,
        'score': None,
        'sent_at': None,
        'status': 'PENDING',
        'survey_id': None,
        'title': None,
        'token_id': None,
        'user_id': None,
        **attrs,
    }


def apply_get_env(envs={}):
    def get_env(key, default=None):
        return envs.get(key, default)

    return get_env


class ActionCertificateScreenshotTestCase(FeedbackTestCase):
    """Test task send_mentorship_session_survey"""
    """
    🔽🔽🔽 Without MentorshipSession
    """
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'ENV': 'test', 'API_URL': API_URL})))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_send_mentorship_session_survey__without_mentorship_session(self):
        from logging import Logger

        send_mentorship_session_survey.delay(1)

        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [])
        self.assertEqual(Logger.debug.call_args_list, [call('Starting send_mentorship_session_survey')])
        self.assertEqual(Logger.error.call_args_list, [call('without-mentorship-session')])
        self.assertEqual(actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 With MentorshipSession and without User (mentee)
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'ENV': 'test', 'API_URL': API_URL})))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_send_mentorship_session_survey__with_mentorship_session(self):
        from logging import Logger

        self.bc.database.create(mentorship_session=1)

        send_mentorship_session_survey.delay(1)

        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [])
        self.assertEqual(Logger.debug.call_args_list, [call('Starting send_mentorship_session_survey')])
        self.assertEqual(Logger.error.call_args_list, [call('mentorship-session-without-mentee')])
        self.assertEqual(actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 With MentorshipSession started not finished and with User (mentee)
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'ENV': 'test', 'API_URL': API_URL})))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__session_started_not_finished(
            self):
        from logging import Logger

        mentorship_session = {
            'started_at': UTC_NOW,
        }
        self.bc.database.create(mentorship_session=mentorship_session, user=1)

        send_mentorship_session_survey.delay(1)

        self.assertEqual(Logger.debug.call_args_list, [call('Starting send_mentorship_session_survey')])
        self.assertEqual(Logger.error.call_args_list, [
            call('mentorship-session-without-started-at-or-ended-at'),
        ])

        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [])
        self.assertEqual(actions.send_email_message.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('authenticate.Token'), [])

    """
    🔽🔽🔽 With MentorshipSession not started but finished and with User (mentee)
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'ENV': 'test', 'API_URL': API_URL})))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__session_not_started_but_finished(
            self):
        from logging import Logger

        mentorship_session = {
            'ended_at': UTC_NOW,
        }
        self.bc.database.create(mentorship_session=mentorship_session, user=1)

        send_mentorship_session_survey.delay(1)

        self.assertEqual(Logger.debug.call_args_list, [call('Starting send_mentorship_session_survey')])
        self.assertEqual(Logger.error.call_args_list, [
            call('mentorship-session-without-started-at-or-ended-at'),
        ])

        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [])
        self.assertEqual(actions.send_email_message.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('authenticate.Token'), [])

    """
    🔽🔽🔽 With MentorshipSession started and finished and with User (mentee)
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'ENV': 'test', 'API_URL': API_URL})))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__session_started_and_finished(
            self):
        from logging import Logger

        mentorship_session = {
            'started_at': UTC_NOW,
            'ended_at': UTC_NOW + timedelta(minutes=5),
        }
        self.bc.database.create(mentorship_session=mentorship_session, user=1)

        send_mentorship_session_survey.delay(1)

        self.assertEqual(Logger.debug.call_args_list, [call('Starting send_mentorship_session_survey')])
        self.assertEqual(Logger.error.call_args_list, [
            call('mentorship-session-duration-less-or-equal-than-five-minutes'),
        ])

        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [])
        self.assertEqual(actions.send_email_message.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('authenticate.Token'), [])

    """
    🔽🔽🔽 With MentorshipSession and with User (mentee)
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'ENV': 'test', 'API_URL': API_URL})))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_send_mentorship_session_survey__with_mentorship_session__with_mentee(self):
        from logging import Logger

        mentorship_session = {
            'started_at': UTC_NOW,
            'ended_at': UTC_NOW + timedelta(minutes=5, seconds=1),
        }
        model = self.bc.database.create(mentorship_session=mentorship_session, user=1)

        send_mentorship_session_survey.delay(1)

        self.assertEqual(Logger.debug.call_args_list, [call('Starting send_mentorship_session_survey')])
        self.assertEqual(Logger.error.call_args_list, [
            call('mentorship-session-not-have-a-service-associated-with-it'),
        ])

        fullname_of_mentor = (model.mentorship_session.mentor.user.first_name + ' ' +
                              model.mentorship_session.mentor.user.last_name)

        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [])
        self.assertEqual(actions.send_email_message.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('authenticate.Token'), [])

    """
    🔽🔽🔽 With MentorshipSession, User (mentee) and MentorshipService
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'ENV': 'test', 'API_URL': API_URL})))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__with_mentorship_service(
            self):
        from logging import Logger

        mentorship_session = {
            'started_at': UTC_NOW,
            'ended_at': UTC_NOW + timedelta(minutes=5, seconds=1),
        }
        model = self.bc.database.create(mentorship_session=mentorship_session, user=1, mentorship_service=1)

        send_mentorship_session_survey.delay(1)

        self.assertEqual(Logger.debug.call_args_list, [call('Starting send_mentorship_session_survey')])
        self.assertEqual(Logger.error.call_args_list, [])

        fullname_of_mentor = (model.mentorship_session.mentor.user.first_name + ' ' +
                              model.mentorship_session.mentor.user.last_name)

        token = self.bc.database.get('authenticate.Token', 1, dict=False)

        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [
            build_answer_dict({
                'academy_id': 1,
                'title': strings['en']['session']['title'].format(fullname_of_mentor),
                'lowest': strings['en']['session']['lowest'],
                'highest': strings['en']['session']['highest'],
                'mentorship_session_id': 1,
                'sent_at': UTC_NOW,
                'status': 'SENT',
                'user_id': 1,
            }),
        ])

        self.assertEqual(actions.send_email_message.call_args_list, [
            call(
                'nps_survey', model.user.email, {
                    'SUBJECT': strings['en']['survey_subject'],
                    'MESSAGE': strings['en']['session']['title'].format(fullname_of_mentor),
                    'TRACKER_URL': f'{API_URL}/v1/feedback/answer/1/tracker.png',
                    'BUTTON': strings['en']['button_label'],
                    'LINK': f'https://nps.breatheco.de/1?token={token.key}'
                })
        ])

        self.bc.check.partial_equality(self.bc.database.list_of('authenticate.Token'),
                                       [{
                                           'key': token.key,
                                           'token_type': 'temporal',
                                       }])

    """
    🔽🔽🔽 With MentorshipSession, with User (mentee) and Answer with status PENDING
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'ENV': 'test', 'API_URL': API_URL})))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__with_answer(self):
        from logging import Logger

        mentorship_session = {
            'started_at': UTC_NOW,
            'ended_at': UTC_NOW + timedelta(minutes=5, seconds=1),
        }
        model = self.bc.database.create(mentorship_session=mentorship_session,
                                        user=1,
                                        answer=1,
                                        mentorship_service=1)

        send_mentorship_session_survey.delay(1)

        self.assertEqual(Logger.debug.call_args_list, [call('Starting send_mentorship_session_survey')])
        self.assertEqual(Logger.error.call_args_list, [])

        token = self.bc.database.get('authenticate.Token', 1, dict=False)

        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [
            {
                **self.bc.format.to_dict(model.answer),
                'sent_at': UTC_NOW,
            },
        ])

        self.assertEqual(actions.send_email_message.call_args_list, [
            call(
                'nps_survey', model.user.email, {
                    'SUBJECT': strings['en']['survey_subject'],
                    'MESSAGE': model.answer.title,
                    'TRACKER_URL': f'{API_URL}/v1/feedback/answer/1/tracker.png',
                    'BUTTON': strings['en']['button_label'],
                    'LINK': f'https://nps.breatheco.de/1?token={token.key}'
                })
        ])

        self.bc.check.partial_equality(self.bc.database.list_of('authenticate.Token'),
                                       [{
                                           'key': token.key,
                                           'token_type': 'temporal',
                                       }])

    """
    🔽🔽🔽 With MentorshipSession, with User (mentee) and Answer with status ANSWERED
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(side_effect=apply_get_env({'ENV': 'test', 'API_URL': API_URL})))
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_send_mentorship_session_survey__with_mentorship_session__with_mentee__with_answer_answered(self):
        from logging import Logger

        answer = {'status': 'ANSWERED'}
        mentorship_session = {
            'started_at': UTC_NOW,
            'ended_at': UTC_NOW + timedelta(minutes=5, seconds=1),
        }
        model = self.bc.database.create(mentorship_session=mentorship_session,
                                        user=1,
                                        answer=answer,
                                        mentorship_service=1)

        send_mentorship_session_survey.delay(1)

        self.assertEqual(Logger.debug.call_args_list, [
            call('Starting send_mentorship_session_survey'),
            call('answer-with-status-answered'),
        ])

        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [self.bc.format.to_dict(model.answer)])
        self.assertEqual(actions.send_email_message.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('authenticate.Token'), [])

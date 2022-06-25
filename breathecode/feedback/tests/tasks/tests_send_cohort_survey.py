"""
Test /academy/survey
"""

from unittest.mock import patch, MagicMock, call

import logging

from ..mixins import FeedbackTestCase
from breathecode.feedback.tasks import send_cohort_survey, generate_user_cohort_survey_answers
import breathecode.feedback.tasks as tasks
from breathecode.feedback.models import Answer
from django.utils import timezone
from datetime import timedelta
import breathecode.notify.actions as actions
from breathecode.utils import ValidationException

now = timezone.now()


def apply_get_env(configuration={}):
    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class SendCohortSurvey(FeedbackTestCase):
    """Test /academy/survey"""
    @patch('breathecode.feedback.tasks.generate_user_cohort_survey_answers', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    def test_send_cohort_survey_when_survey_is_none(self):

        model = self.generate_models(cohort=1)

        send_cohort_survey(user_id=None, survey_id=None)

        self.assertEqual(logging.Logger.debug.call_args_list, [call('Starting send_cohort_survey')])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Survey not found')])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [])
        self.assertEqual(tasks.generate_user_cohort_survey_answers.call_args_list, [])

    @patch('breathecode.feedback.tasks.generate_user_cohort_survey_answers', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    def test_send_cohort_survey_when_user_is_none(self):

        model = self.generate_models(cohort=1, survey=1)

        send_cohort_survey(survey_id=1, user_id=None)

        self.assertEqual(logging.Logger.debug.call_args_list, [call('Starting send_cohort_survey')])
        self.assertEqual(logging.Logger.error.call_args_list, [call('User not found')])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [self.bc.format.to_dict(model.survey)])
        self.assertEqual(tasks.generate_user_cohort_survey_answers.call_args_list, [])

    @patch('breathecode.feedback.tasks.generate_user_cohort_survey_answers', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    def test_send_cohort_survey_when_survey_has_expired(self):

        created = timezone.now() - timedelta(hours=48, minutes=1)
        duration = timedelta(hours=48)

        model = self.generate_models(cohort=1, survey={'duration': duration}, user=1)

        model.survey.created_at = created

        model.survey.save()

        send_cohort_survey(survey_id=1, user_id=1)

        self.assertEqual(logging.Logger.debug.call_args_list, [call('Starting send_cohort_survey')])
        self.assertEqual(logging.Logger.error.call_args_list, [call('This survey has already expired')])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [self.bc.format.to_dict(model.survey)])
        self.assertEqual(tasks.generate_user_cohort_survey_answers.call_args_list, [])

    @patch('breathecode.feedback.tasks.generate_user_cohort_survey_answers', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_send_cohort_when_student_does_not_belong_to_cohort(self):

        model = self.generate_models(cohort=1, user=1, survey=1)

        send_cohort_survey(survey_id=1, user_id=1)

        self.assertEqual(logging.Logger.debug.call_args_list, [call('Starting send_cohort_survey')])
        self.assertEqual(logging.Logger.error.call_args_list,
                         [call('This student does not belong to this cohort')])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [self.bc.format.to_dict(model.survey)])
        self.assertEqual(tasks.generate_user_cohort_survey_answers.call_args_list, [])
        self.assertEqual(actions.send_email_message.call_args_list, [])

    @patch('breathecode.feedback.tasks.generate_user_cohort_survey_answers', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_send_cohort_survey_when_an_email_is_sent(self):

        model = self.generate_models(cohort=1, user=1, survey=1, cohort_user={'role': 'STUDENT'})

        send_cohort_survey(survey_id=1, user_id=1)

        self.assertEqual(logging.Logger.debug.call_args_list, [call('Starting send_cohort_survey')])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [self.bc.format.to_dict(model.survey)])
        self.assertEqual(tasks.generate_user_cohort_survey_answers.call_args_list,
                         [call(model.user, model.survey, status='SENT')])
        token = self.bc.database.get('authenticate.Token', 1, dict=False)
        self.assertEqual(actions.send_email_message.call_args_list, [
            call(
                'nps_survey', model.user.email, {
                    'SUBJECT': 'We need your feedback',
                    'MESSAGE':
                    'Please take 5 minutes to give us feedback about your experience at the academy so far.',
                    'TRACKER_URL': 'https://breathecode.herokuapp.com/v1/feedback/survey/1/tracker.png',
                    'BUTTON': 'Answer the question',
                    'LINK': f'https://nps.breatheco.de/survey/1?token={token.key}'
                })
        ])

    @patch('os.getenv',
           MagicMock(side_effect=apply_get_env({'API_URL': 'https://breathecode.herokuapp.com'})))
    @patch('breathecode.feedback.tasks.generate_user_cohort_survey_answers', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('breathecode.notify.actions.send_slack', MagicMock())
    def test_send_cohort_survey_when_an_email_is_sent_with_slack_team_and_user(self):

        model = self.generate_models(cohort=1,
                                     slack_user=1,
                                     slack_team=1,
                                     user=1,
                                     survey=1,
                                     cohort_user={'role': 'STUDENT'})

        send_cohort_survey(survey_id=1, user_id=1)

        self.assertEqual(logging.Logger.debug.call_args_list, [call('Starting send_cohort_survey')])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [self.bc.format.to_dict(model.survey)])
        self.assertEqual(tasks.generate_user_cohort_survey_answers.call_args_list,
                         [call(model.user, model.survey, status='SENT')])
        print(actions.send_slack.call_args_list)
        token = self.bc.database.get('authenticate.Token', 1, dict=False)
        print([
            call('nps_survey',
                 model.slack_user,
                 model.slack_team,
                 data={
                     'SUBJECT': 'We need your feedback',
                     'MESSAGE':
                     'Please take 5 minutes to give us feedback about your experience at the academy so far.',
                     'TRACKER_URL': 'https://breathecode.herokuapp.com/v1/feedback/survey/1/tracker.png',
                     'BUTTON': 'Answer the question',
                     'LINK': f'https://nps.breatheco.de/survey/1?token={token.key}'
                 })
        ])
        self.assertEqual(actions.send_slack.call_args_list, [
            call('nps_survey',
                 model.slack_user,
                 model.slack_team,
                 data={
                     'SUBJECT': 'We need your feedback',
                     'MESSAGE':
                     'Please take 5 minutes to give us feedback about your experience at the academy so far.',
                     'TRACKER_URL': 'https://breathecode.herokuapp.com/v1/feedback/survey/1/tracker.png',
                     'BUTTON': 'Answer the question',
                     'LINK': f'https://nps.breatheco.de/survey/1?token={token.key}'
                 })
        ])
        self.assertEqual(actions.send_email_message.call_args_list, [
            call(
                'nps_survey', model.user.email, {
                    'SUBJECT': 'We need your feedback',
                    'MESSAGE':
                    'Please take 5 minutes to give us feedback about your experience at the academy so far.',
                    'TRACKER_URL': 'https://breathecode.herokuapp.com/v1/feedback/survey/1/tracker.png',
                    'BUTTON': 'Answer the question',
                    'LINK': f'https://nps.breatheco.de/survey/1?token={token.key}'
                })
        ])

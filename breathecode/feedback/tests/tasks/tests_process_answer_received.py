"""
Test /academy/survey
"""
import re, urllib
from unittest.mock import patch, MagicMock, call
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import FeedbackTestCase
from breathecode.feedback.tasks import process_answer_received


class SurveyAnsweredTestSuite(FeedbackTestCase):
    """Test /academy/survey"""
    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_survey_answered_task_without_answer(self):

        from breathecode.feedback.signals import survey_answered
        import logging

        model = self.generate_models()

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [call('Answer not found')])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [])

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_survey_answered_task_without_survey(self):

        from breathecode.feedback.signals import survey_answered
        import logging

        model = self.generate_models(answer=1)

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [call('No survey connected to answer.')])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [])

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_survey_answered_task_with_survey(self):

        from breathecode.feedback.signals import survey_answered
        import logging

        model = self.generate_models(answer=1, survey=1)
        survey_db = self.model_to_dict(model, 'survey')

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [{
            **survey_db,
            'response_rate': 0.0,
        }])

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_survey_answered_task_with_survey_score_seven(self):

        from breathecode.feedback.signals import survey_answered
        from breathecode.notify.actions import send_email_message
        import logging

        answer = {'score': 7}
        model = self.generate_models(answer=answer, survey=1)
        survey_db = self.model_to_dict(model, 'survey')

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(send_email_message.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [{
            **survey_db,
            'avg_score': '7.0',
            'response_rate': 0.0,
        }])

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_survey_answered_task_with_survey_score_seven__with_academy(self):

        from breathecode.feedback.signals import survey_answered
        from breathecode.notify.actions import send_email_message
        import logging

        answer = {'score': 7}
        model = self.generate_models(answer=answer, survey=1, academy=1)
        survey_db = self.model_to_dict(model, 'survey')

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(send_email_message.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [{
            **survey_db,
            'avg_score': '7.0',
            'response_rate': 0.0,
        }])

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_survey_answered_task_with_survey_score_seven__with_academy__with_user__without_feedback_email(
            self):

        from breathecode.feedback.signals import survey_answered
        from breathecode.notify.actions import send_email_message
        import logging, os

        SYSTEM_EMAIL = os.getenv('SYSTEM_EMAIL', '')

        answer_kwargs = {'score': 7}
        list_of_emails = [SYSTEM_EMAIL]
        model = self.generate_models(answer=answer_kwargs, survey=1, academy=1, user=1)
        survey_db = self.model_to_dict(model, 'survey')

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        print(send_email_message.call_args_list)
        self.assertEqual(send_email_message.call_args_list, [
            call('negative_answer', ['something@email.com', f'{model.academy.feedback_email}'],
                 data={
                     'SUBJECT': f'A student answered with a bad NPS score at {model.answer.academy.name}',
                     'FULL_NAME': f'{model.answer.user.first_name} {model.answer.user.last_name}',
                     'QUESTION': model.answer.title,
                     'SCORE': model.answer.score,
                     'COMMENTS': model.answer.comment,
                     'ACADEMY': model.answer.academy.name,
                     'LINK': f'https://admin.breatheco.de/feedback/surveys/{model.answer.academy.slug}/1'
                 })
        ])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [{
            **survey_db,
            'avg_score': '7.0',
            'response_rate': 0.0,
        }])

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_survey_answered_task_with_survey_score_seven__with_academy__with_user__with_feedback_email(self):

        from breathecode.feedback.signals import survey_answered
        from breathecode.notify.actions import send_email_message
        import logging

        answer_kwargs = {'score': 7}
        academy_kwargs = {'feedback_email': 'test@email.com'}
        model = self.generate_models(answer=answer_kwargs, survey=1, academy=academy_kwargs, user=1)
        survey_db = self.model_to_dict(model, 'survey')

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        print(send_email_message.call_args_list)
        self.assertEqual(send_email_message.call_args_list, [
            call('negative_answer', ['something@email.com', f'{model.academy.feedback_email}'],
                 data={
                     'SUBJECT': f'A student answered with a bad NPS score at {model.answer.academy.name}',
                     'FULL_NAME': f'{model.answer.user.first_name} {model.answer.user.last_name}',
                     'QUESTION': model.answer.title,
                     'SCORE': model.answer.score,
                     'COMMENTS': model.answer.comment,
                     'ACADEMY': model.answer.academy.name,
                     'LINK': f'https://admin.breatheco.de/feedback/surveys/{model.answer.academy.slug}/1'
                 })
        ])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [{
            **survey_db,
            'avg_score': '7.0',
            'response_rate': 0.0,
        }])

    @patch('logging.Logger.warn', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    def test_survey_answered_task_with_survey_score_ten__with_academy__with_user(self):

        from breathecode.feedback.signals import survey_answered
        from breathecode.notify.actions import send_email_message
        import logging

        answer = {'score': 10}
        model = self.generate_models(answer=answer, survey=1, academy=1, user=1)
        survey_db = self.model_to_dict(model, 'survey')

        process_answer_received.delay(1)

        self.assertEqual(logging.Logger.warn.call_args_list, [])
        self.assertEqual(logging.Logger.error.call_args_list, [])
        self.assertEqual(send_email_message.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [{
            **survey_db,
            'avg_score': '10.0',
            'response_rate': 0.0,
        }])

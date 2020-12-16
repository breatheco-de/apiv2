"""
Test /answer
"""
from breathecode.notify.actions import get_template_content
import os
from datetime import datetime
from unittest.mock import call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    MAILGUN_PATH,
    MAILGUN_INSTANCES,
    apply_requests_post_mock,
)
from ..mixins import FeedbackTestCase
from ...actions import send_survey, strings

class SendSurveyTestSuite(FeedbackTestCase):
    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_send_survey_without_cohort(self):
        """Test /answer without auth"""
        model = self.generate_models(user=True)
        
        try:
            send_survey(model['user'])
        except Exception as e:
            self.assertEquals(str(e), ('Impossible to determine the student cohort, maybe it has '
                'more than one, or cero.'))

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH['post'], apply_requests_post_mock())
    def test_send_survey_wit_one_user_with_two_cohort(self):
        """Test /answer without auth"""
        model = self.generate_models(cohort_user=True, cohort_user_two=True)
        
        try:
            send_survey(model['user'])
        except Exception as e:
            self.assertEquals(str(e), ('Impossible to determine the student cohort, maybe it has '
                'more than one, or cero.'))

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH['post'], apply_requests_post_mock())
    def test_send_survey_with_cohort_lang_en(self):
        """Test /answer without auth"""
        mock = MAILGUN_INSTANCES['post']
        mock.call_args_list = []

        model = self.generate_models(user=True, cohort_user=True, lang='en')
        academy = model['cohort'].academy.name
        
        send_survey(model['user'])
        expected = [{
            'academy_id': 1,
            'cohort_id': 1,
            'comment': None,
            'event_id': None,
            'highest': 'very likely',
            'id': 1,
            'lang': 'en',
            'lowest': 'not likely',
            'mentor_id': None,
            'opened_at': None,
            'score': None,
            'status': 'SENT',
            'title': f'How likely are you to recommend {academy} to your friends and family?',
            'user_id': 1,
            'token_id': 1,
        }]

        dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
            datetime) and answer.pop('created_at')]
        self.assertEqual(dicts, expected)
        self.check_email_contain_a_correct_token('en', academy, dicts, mock, model)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH['post'], apply_requests_post_mock())
    def test_send_survey_with_cohort_lang_es(self):
        """Test /answer without auth"""
        mock = MAILGUN_INSTANCES['post']
        mock.call_args_list = []

        model = self.generate_models(user=True, cohort_user=True, lang='es')
        academy = model['cohort'].academy.name

        send_survey(model['user'])
        expected = [{
            'academy_id': 1,
            'cohort_id': 1,
            'comment': None,
            'event_id': None,
            'highest': 'muy probable',
            'id': 1,
            'lang': 'es',
            'lowest': 'no es probable',
            'mentor_id': None,
            'opened_at': None,
            'score': None,
            'status': 'SENT',
            'title': f'¿Qué tan probable es que recomiendes {academy} a tus amigos y familiares?',
            'user_id': 1,
            'token_id': 1,
        }]

        # print(mock.call_args_list)

        dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
            datetime) and answer.pop('created_at')]
        self.assertEqual(dicts, expected)
        self.assertEqual(self.count_token(), 1)
        self.check_email_contain_a_correct_token('es', academy, dicts, mock, model)

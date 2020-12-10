"""
Test /answer
"""
import re
from datetime import datetime
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import FeedbackTestCase
from ...actions import send_survey

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
    def test_send_survey_with_cohort_lang_en(self):
        """Test /answer without auth"""
        model = self.generate_models(user=True, cohort_user=True, lang='en')
        academy = model['cohort'].academy.name
        
        print(model.keys())
        send_survey(model['user'])
        print(model['cohort'].academy.name)
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
        }]

        dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
            datetime) and answer.pop('created_at')]
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_send_survey_with_cohort_lang_es(self):
        """Test /answer without auth"""
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
        }]

        dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
            datetime) and answer.pop('created_at')]
        self.assertEqual(dicts, expected)

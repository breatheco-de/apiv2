"""
Test /answer
"""
import re
from datetime import datetime
from unittest.mock import call, patch
from django.http.request import HttpRequest
from django.contrib.auth.models import User
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    DJANGO_CONTRIB_PATH,
    DJANGO_CONTRIB_INSTANCES,
    apply_django_contrib_messages_mock,
)
from ..mixins import FeedbackTestCase
from ...admin import send_bulk_cohort_user_survey
from ...models import CohortUser

class SendSurveyTestSuite(FeedbackTestCase):
    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_send_bulk_cohort_user_survey__without_cohort(self):
        """Test /answer without auth"""
        request = HttpRequest()
        mock = DJANGO_CONTRIB_INSTANCES['messages']
        mock.success.call_args_list = []
        mock.error.call_args_list = []

        self.assertEqual(send_bulk_cohort_user_survey(None, request, CohortUser.objects.all()), None)
        self.assertEqual(mock.success.call_args_list, [call(request, message='Survey was '
            'successfully sent')])
        self.assertEqual(mock.error.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_send_bulk_cohort_user_survey_with_success_models(self):
        """Test /answer without auth"""
        request = HttpRequest()
        mock = DJANGO_CONTRIB_INSTANCES['messages']
        mock.success.call_args_list = []
        mock.error.call_args_list = []

        models = [self.generate_models(user=True, cohort_user=True, lang='en') for _ in range(0, 3)]
        academies = [(models[key]['cohort'].academy.name, key + 1) for key in range(0, 3)]
        
        self.assertEqual(send_bulk_cohort_user_survey(None, request, CohortUser.objects.all()), None)
        self.assertEqual(mock.success.call_args_list, [call(request, message='Survey was '
            'successfully sent')])
        self.assertEqual(mock.error.call_args_list, [])
        expected = [{
            'academy_id': key,
            'cohort_id': key,
            'comment': None,
            'event_id': None,
            'highest': 'very likely',
            'id': key,
            'lang': 'en',
            'lowest': 'not likely',
            'mentor_id': None,
            'opened_at': None,
            'score': None,
            'status': 'SENT',
            'title': f'How likely are you to recommend {academy} to your friends and family?',
            'user_id': key,
        } for academy, key in academies]

        dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
            datetime) and answer.pop('created_at')]
        self.assertEqual(dicts, expected)

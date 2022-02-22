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


class SurveyTestSuite(FeedbackTestCase):
    """Test /academy/survey"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey_without_auth(self):
        """Test /academy/survey without auth"""
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey_without_academy(self):
        """Test /academy/survey without academy"""
        self.bc.database.create(authenticate=True)
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey_without_data(self):
        """Test /academy/survey without data"""
        self.headers(academy=1)
        url = reverse_lazy('feedback:academy_survey')
        self.bc.database.create(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_survey for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_data(self):
        """Test /academy/survey with data"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
        )

        db = self.model_to_dict(model, 'survey')
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['survey'].id,
            'lang': model['survey'].lang,
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name
            },
            'avg_score': model['survey'].avg_score,
            'response_rate': model['survey'].response_rate,
            'status': model['survey'].status,
            'duration': '86400.0',
            'created_at': self.bc.datetime.to_iso_string(model['survey'].created_at),
            'sent_at': None,
            'public_url': 'https://nps.breatheco.de/survey/1'
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_academy_survey__get__with_status_answered(self):
        """Test /academy/survey with status answered"""

        from breathecode.feedback.signals import survey_answered

        self.headers(academy=1)
        survey = {'status': 'SENT'}
        answer = {'status': 'ANSWERED'}
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=survey,
            answer=answer,
            capability='read_survey',
        )

        db = self.model_to_dict(model, 'survey')
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['survey'].id,
            'lang': model['survey'].lang,
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name
            },
            'avg_score': model['survey'].avg_score,
            'response_rate': model['survey'].response_rate,
            'status': model['survey'].status,
            'duration': '86400.0',
            'created_at': self.bc.datetime.to_iso_string(model['survey'].created_at),
            'sent_at': None,
            'public_url': 'https://nps.breatheco.de/survey/1'
        }]
        expected_args_list = [call(instance=model.answer, sender=model.answer.__class__)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(survey_answered.send.call_args_list, expected_args_list)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    @patch('breathecode.feedback.tasks.process_answer_received.delay', MagicMock())
    def test_academy_survey__get__with_status_answered_call_signal(self):
        """Test /academy/survey with data"""

        from breathecode.feedback.signals import survey_answered
        from breathecode.feedback.tasks import process_answer_received

        self.headers(academy=1)
        survey = {'status': 'SENT'}
        answer = {'status': 'ANSWERED'}
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=survey,
            answer=answer,
            capability='read_survey',
        )

        survey_db = self.model_to_dict(model, 'survey')
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['survey'].id,
            'lang': model['survey'].lang,
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name
            },
            'avg_score': model['survey'].avg_score,
            'response_rate': model['survey'].response_rate,
            'status': model['survey'].status,
            'duration': '86400.0',
            'created_at': self.bc.datetime.to_iso_string(model['survey'].created_at),
            'sent_at': None,
            'public_url': 'https://nps.breatheco.de/survey/1'
        }]

        signal_expected_args_list = [call(instance=model.answer, sender=model.answer.__class__)]
        task_expected_args_list = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(survey_answered.send.call_args_list, signal_expected_args_list)
        self.assertEqual(process_answer_received.delay.call_args_list, task_expected_args_list)
        self.assertEqual(self.all_survey_dict(), [survey_db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.feedback.tasks.process_answer_received.delay', MagicMock())
    def test_academy_survey__get__with_status_answered_call_task(self):
        """Test /academy/survey with data"""

        from breathecode.feedback.tasks import process_answer_received

        self.headers(academy=1)
        survey = {'status': 'SENT'}
        answer = {'status': 'ANSWERED'}
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=survey,
            answer=answer,
            capability='read_survey',
        )

        survey_db = self.model_to_dict(model, 'survey')
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['survey'].id,
            'lang': model['survey'].lang,
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name
            },
            'avg_score': model['survey'].avg_score,
            'response_rate': model['survey'].response_rate,
            'status': model['survey'].status,
            'duration': '86400.0',
            'created_at': self.bc.datetime.to_iso_string(model['survey'].created_at),
            'sent_at': None,
            'public_url': 'https://nps.breatheco.de/survey/1'
        }]

        task_expected_args_list = [call(1)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(process_answer_received.delay.call_args_list, task_expected_args_list)
        self.assertEqual(self.all_survey_dict(), [survey_db])

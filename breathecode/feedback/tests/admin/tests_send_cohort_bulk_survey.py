"""
Test /answer
"""
from datetime import datetime
from unittest.mock import patch
from django.http.request import HttpRequest
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import FeedbackTestCase
from ...admin import send_cohort_bulk_survey
from ...models import Cohort

class SendSurveyTestSuite(FeedbackTestCase):
    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_without_cohort(self):
        """Test /answer without auth"""
        request = HttpRequest()

        self.assertEqual(send_cohort_bulk_survey(None, request, Cohort.objects.all()), None)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_with_educational_status_active(self):
        """Test /answer without auth"""
        request = HttpRequest()

        models = [self.generate_models(user=True, cohort_user=True, profile_academy=True,
            cohort_user_role='STUDENT', educational_status='ACTIVE', lang='en') for _ in range(0, 3)]
        academies = [(models[key]['cohort'].academy.name, key + 1) for key in range(0, 3)]
        
        self.assertEqual(send_cohort_bulk_survey(None, request, Cohort.objects.all()), None)
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
            'token_id': key,
            'user_id': key,
        } for academy, key in academies]

        dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
            datetime) and answer.pop('created_at')]
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_with_educational_status_graduated(self):
        """Test /answer without auth"""
        request = HttpRequest()

        models = [self.generate_models(user=True, cohort_user=True, profile_academy=True,
            cohort_user_role='STUDENT', educational_status='GRADUATED', lang='en') for _ in range(0, 3)]
        academies = [(models[key]['cohort'].academy.name, key + 1) for key in range(0, 3)]
        
        self.assertEqual(send_cohort_bulk_survey(None, request, Cohort.objects.all()), None)
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
            'token_id': key,
            'user_id': key,
        } for academy, key in academies]

        dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
            datetime) and answer.pop('created_at')]
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_with_educational_status_postponed(self):
        """Test /answer without auth"""
        request = HttpRequest()

        models = [self.generate_models(user=True, cohort_user=True, profile_academy=True,
            cohort_user_role='STUDENT', educational_status='POSTPONED', lang='en') for _ in range(0, 3)]
        academies = [(models[key]['cohort'].academy.name, key + 1) for key in range(0, 3)]
        
        self.assertEqual(send_cohort_bulk_survey(None, request, Cohort.objects.all()), None)
        expected = []

        dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
            datetime) and answer.pop('created_at')]
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_with_educational_status_suspended(self):
        """Test /answer without auth"""
        request = HttpRequest()

        models = [self.generate_models(user=True, cohort_user=True, profile_academy=True,
            cohort_user_role='STUDENT', educational_status='SUSPENDED', lang='en') for _ in range(0, 3)]
        academies = [(models[key]['cohort'].academy.name, key + 1) for key in range(0, 3)]
        
        self.assertEqual(send_cohort_bulk_survey(None, request, Cohort.objects.all()), None)
        expected = []

        dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
            datetime) and answer.pop('created_at')]
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_with_educational_status_dropped(self):
        """Test /answer without auth"""
        request = HttpRequest()

        models = [self.generate_models(user=True, cohort_user=True, profile_academy=True,
            cohort_user_role='STUDENT', educational_status='DROPPED', lang='en') for _ in range(0, 3)]
        academies = [(models[key]['cohort'].academy.name, key + 1) for key in range(0, 3)]
        
        self.assertEqual(send_cohort_bulk_survey(None, request, Cohort.objects.all()), None)
        expected = []

        dicts = [answer for answer in self.all_answer_dict() if isinstance(answer['created_at'],
            datetime) and answer.pop('created_at')]
        self.assertEqual(dicts, expected)

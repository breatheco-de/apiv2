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
    def test_academy_survey__get__without_auth(self):
        """Test /academy/survey without authorization"""
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__without_academy(self):
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
    def test_academy_survey__get__without_role(self):
        """Test /academy/survey without role"""
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
    def test_academy_survey__get__without_data(self):
        """Test /academy/survey without data"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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
    def test_academy_survey__get__with_sent_status_query(self):
        """Test /academy/survey with sent status query"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey') + '?status=SENT'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_pending_status_query(self):
        """Test /academy/survey with pending status query"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey') + '?status=PENDING'
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
    def test_academy_survey__get__with_different_lang_query(self):
        """Test /academy/survey with different lang status query"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey') + '?lang=esp'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_same_lang_query(self):
        """Test /academy/survey with same lang status query"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey') + '?lang=en'
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
    def test_academy_survey__get__with_different_cohort_slug_cohort_query(self):
        """Test /academy/survey with different cohort slug than what in the cohort query"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
            cohort=True,
        )

        url = reverse_lazy('feedback:academy_survey') + f'?cohort=testing-cohort'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_same_cohort_slug_cohort_query(self):
        """Test /academy/survey with same chort slug that is in the model"""

        self.headers(academy=1)
        cohort_kwargs = {'slug': 'testing-cohort'}
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
            cohort=cohort_kwargs,
        )

        url = reverse_lazy('feedback:academy_survey') + f'?cohort=testing-cohort'
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
    def test_academy_survey__post__without_auth(self):
        """Test /academy/survey without authorization"""
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url, {})
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__without_academy(self):
        """Test /academy/survey without authorization"""
        self.bc.database.create(authenticate=True)
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url, {})
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
    def test_academy_survey__post__without_role(self):
        """Test /academy/survey without authorization"""
        self.headers(academy=1)
        url = reverse_lazy('feedback:academy_survey')
        self.bc.database.create(authenticate=True)
        response = self.client.post(url, {})
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: crud_survey for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__without_cohort(self):
        """Test /academy/survey post without data"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='crud_survey',
            capability='crud_survey',
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url)
        json = response.json()
        expected = {'cohort': ['This field is required.']}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__without_teacher_assigned(self):
        """Test /academy/survey post without data"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='crud_survey',
            capability='crud_survey',
            cohort=True,
            cohort_user=True,
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url, {'cohort': 1})
        json = response.json()
        expected = {
            'detail': 'This cohort must have a teacher assigned to be able to survey it',
            'status_code': 400
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__with_teacher_assigned(self):
        """Test /academy/survey post without data"""

        self.headers(academy=1)
        cohort_user_kwargs = {'role': 'TEACHER'}
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='TEACHER',
            capability='crud_survey',
            cohort=True,
            cohort_user=cohort_user_kwargs,
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url, {'cohort': 1})
        json = response.json()

        del json['created_at']
        del json['updated_at']

        expected = {
            'id': model['cohort'].id,
            'status': True,
            'public_url': 'https://nps.breatheco.de/survey/1',
            'lang': 'en',
            'max_assistants_to_ask': 2,
            'max_teachers_to_ask': 1,
            'duration': '1 00:00:00',
            # 'created_at': self.bc.datetime.to_iso_string(model['cohort'].created_at),
            # 'updated_at': self.bc.datetime.to_iso_string(model['cohort'].updated_at),
            'sent_at': None,
            'cohort': model['cohort_user'].cohort.id,
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert False

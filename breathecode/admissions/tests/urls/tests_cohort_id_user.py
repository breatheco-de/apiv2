"""
Test /cohort/:id/user
"""
import re
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import AdmissionsTestCase

class CohortIdUserIdTestSuite(AdmissionsTestCase):
    """Test /cohort/:id/user"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_bad_cohort_id(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': 999})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'details': 'Missing cohort_id or user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_bad_user(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {
            'user': 999
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'details': 'invalid user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_without_user(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'details': 'Missing cohort_id or user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_without_profile_academy(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {
            'user':  self.user.id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'details': 'Specified cohort not be found', 'status_code': 500}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {
            'user':  self.user.id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'id': 1,
            'user': {
                'id': self.user.id,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'email': self.user.email,
            },
            'cohort': {
                'id': self.cohort.id,
                'slug': self.cohort.slug,
                'name': self.cohort.name,
                'kickoff_date': re.sub(
                    r'\+00:00$', 'Z',
                    self.cohort.kickoff_date.isoformat()
                ),
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

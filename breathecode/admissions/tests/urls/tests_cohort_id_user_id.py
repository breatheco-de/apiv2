"""
Test /cohort/:id/user/:id
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
    """Test /cohort/:id/user/:id"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_without_auth(self):
        """Test /cohort/:id/user/:id without auth"""
        url = reverse_lazy('admissions:cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_put_with_bad_id(self):
        """Test /cohort/:id/user/:id without auth"""
        url = reverse_lazy('admissions:cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'status_code': 500, 'details': 'Specified cohort and user could not be found'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_put_with_id_but_without_user(self):
        """Test /cohort/:id/user/:id without auth"""
        self.generate_models(authenticate=True, cohort=True)
        url = reverse_lazy('admissions:cohort_id_user_id', kwargs={'cohort_id': self.cohort.id,
            'user_id': self.user.id})
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'status_code': 500, 'details': 'Specified cohort and user could not be found'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_put_with_id_but_with_user(self):
        """Test /cohort/:id/user/:id without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True)
        url = reverse_lazy('admissions:cohort_id_user_id', kwargs={'cohort_id': self.cohort.id,
            'user_id': self.user.id})
        data = {}
        response = self.client.put(url, data)
        json = response.json()
        expected = {'status_code': 500, 'details': 'Specified cohort and user could not be found'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_put_with_id(self):
        """Test /cohort/:id/user/:id without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user_id', kwargs={'cohort_id': self.cohort.id,
            'user_id': self.user.id})
        data = {
            'certificate': self.certificate.id
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'id': self.cohort_user.id,
            'role': self.cohort_user.role,
            'educational_status': self.cohort_user.educational_status,
            'finantial_status': self.cohort_user.finantial_status,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_delete_with_id_with_bad_user_id(self):
        """Test /cohort/:id/user/:id without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user_id', kwargs={'cohort_id': self.cohort.id,
            'user_id': 9999})
        data = {
            'certificate': self.certificate.id
        }
        response = self.client.delete(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_delete_with_id_with_bad_cohort_id(self):
        """Test /cohort/:id/user/:id without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user_id', kwargs={'cohort_id': 9999,
            'user_id': self.user.id})
        data = {
            'certificate': self.certificate.id
        }
        response = self.client.delete(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_id_delete_with_id(self):
        """Test /cohort/:id/user/:id without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user_id', kwargs={'cohort_id': self.cohort.id,
            'user_id': self.user.id})
        data = {
            'certificate': self.certificate.id
        }
        response = self.client.delete(url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.count_cohort_user(), 0)

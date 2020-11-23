"""
Test /academy
"""
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

class academyTestSuite(AdmissionsTestCase):
    """Test /academy"""

    def test_academy_without_auth(self):
        """Test /academy without auth"""
        url = reverse_lazy('admissions:academy')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_without_data(self):
        """Test /academy without auth"""
        url = reverse_lazy('admissions:academy')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_with_data(self):
        """Test /academy without auth"""
        url = reverse_lazy('admissions:academy')
        self.generate_models(authenticate=True, academy=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': self.academy.id,
            'name': self.academy.name,
            'slug': self.academy.slug,
            'street_address': self.academy.street_address,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_new_without_require_fields(self):
        """Test /academy without auth"""
        url = reverse_lazy('admissions:academy')
        self.generate_models(authenticate=True, academy=True)
        data = {}
        response = self.client.post(url, data)
        json = response.json()

        self.assertEqual(json, {
            'slug': ['This field is required.'],
            'name': ['This field is required.'],
            'street_address': ['This field is required.']
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_new_element(self):
        """Test /academy without auth"""
        url = reverse_lazy('admissions:academy')
        self.generate_models(authenticate=True)
        data = {
            'slug': 'oh-my-god',
            'name': 'they killed kenny',
            'street_address': 'you bastards'
        }
        response = self.client.post(url, data)
        json = response.json()

        expected = { 'id': 1 }
        expected.update(data)
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return expected

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_with_data_after_post(self):
        """Test /academy without auth"""
        expected = self.test_academy_new_element()
        url = reverse_lazy('admissions:academy')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [expected])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

"""
Test /certificate
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
from ..mixins.new_admissions_test_case import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""
    def test_certificate_without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:certificate_slug',
                           kwargs={'certificate_slug': 'they-killed-kenny'})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_certificate_dict(), [])

    def test_certificate_without_data(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:certificate_slug',
                           kwargs={'certificate_slug': 'they-killed-kenny'})
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {'status_code': 404, 'detail': 'Certificate slug not found'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_certificate_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_with_data(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True, certificate=True)
        url = reverse_lazy(
            'admissions:certificate_slug',
            kwargs={'certificate_slug': model['certificate'].slug})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'id': model['certificate'].id,
                'name': model['certificate'].name,
                'slug': model['certificate'].slug,
                'logo': model['certificate'].logo,
                'duration_in_days': model['certificate'].duration_in_days,
                'description': model['certificate'].description,
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            self.all_certificate_dict(),
            [{
                'description': model['certificate'].description,
                'duration_in_days': model['certificate'].duration_in_days,
                'duration_in_hours': model['certificate'].duration_in_hours,
                'id': model['certificate'].id,
                'logo': model['certificate'].logo,
                'name': model['certificate'].name,
                'schedule_type': model['certificate'].schedule_type,
                'slug': model['certificate'].slug,
                'week_hours': model['certificate'].week_hours
            }])

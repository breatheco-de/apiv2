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
from ..mixins import AdmissionsTestCase


class CertificateTestSuite(AdmissionsTestCase):
    """Test /certificate"""
    def test_certificate_without_auth(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:schedule_slug', kwargs={'certificate_slug': 'they-killed-kenny'})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_specialty_mode_dict(), [])

    def test_certificate_without_data(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:schedule_slug', kwargs={'certificate_slug': 'they-killed-kenny'})
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {'status_code': 404, 'detail': 'Certificate slug not found'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_specialty_mode_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_with_data(self):
        """Test /certificate without auth"""
        model = self.generate_models(authenticate=True, specialty_mode=True, syllabus=True)
        url = reverse_lazy('admissions:schedule_slug',
                           kwargs={'certificate_slug': model['specialty_mode'].slug})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'id': model['specialty_mode'].id,
                'name': model['specialty_mode'].name,
                'slug': model['specialty_mode'].slug,
                'description': model['specialty_mode'].description,
                'syllabus': model['specialty_mode'].syllabus.id,
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_specialty_mode_dict(), [{
            **self.model_to_dict(model, 'specialty_mode'),
        }])

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
        url = reverse_lazy('admissions:certificate')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_certificate_without_data(self):
        """Test /certificate without auth"""
        url = reverse_lazy('admissions:certificate')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_certificate(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_with_data(self):
        """Test /certificate without auth"""
        self.generate_models(authenticate=True, certificate=True)
        model_dict = self.remove_dinamics_fields(self.certificate.__dict__)
        url = reverse_lazy('admissions:certificate')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': self.certificate.id,
            'name': self.certificate.name,
            'slug': self.certificate.slug,
            'logo': self.certificate.logo,	
            'description': self.certificate.description,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_certificate(), 1)
        self.assertEqual(self.get_certificate_dict(1), model_dict)

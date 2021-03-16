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
        model = self.generate_models(authenticate=True, certificate=True)
        url = reverse_lazy('admissions:certificate')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': model['certificate'].id,
            'name': model['certificate'].name,
            'slug': model['certificate'].slug,
            'logo': model['certificate'].logo,
            'description': model['certificate'].description,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_certificate_dict(), [{
            **self.model_to_dict(model, 'certificate'),
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_with_data_without_pagination_get_just_100(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [self.generate_models(certificate=True, models=base) for _ in range(0, 105)]
        url = reverse_lazy('admissions:certificate')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': model['certificate'].id,
            'name': model['certificate'].name,
            'slug': model['certificate'].slug,
            'logo': model['certificate'].logo,
            'description': model['certificate'].description,
        } for model in models if model['certificate'].id <= 100])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.all_certificate_dict(), [{
            **self.model_to_dict(model, 'certificate'),
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_with_data_with_pagination_first_five(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [self.generate_models(certificate=True, models=base) for _ in range(0, 10)]
        url = reverse_lazy('admissions:certificate') + '?limit=5&offset=0'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'count': 10,
            'first': None,
            'last': 'http://testserver/v1/admissions/certificate?limit=5&offset=5',
            'next': 'http://testserver/v1/admissions/certificate?limit=5&offset=5',
            'previous': None,
            'results': [{
                'id': model['certificate'].id,
                'name': model['certificate'].name,
                'slug': model['certificate'].slug,
                'logo': model['certificate'].logo,
                'description': model['certificate'].description,
            } for model in models if model['certificate'].id <= 5]
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_certificate_dict(), [{
            **self.model_to_dict(model, 'certificate'),
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_with_data_with_pagination_last_five(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [self.generate_models(certificate=True, models=base) for _ in range(0, 10)]
        url = reverse_lazy('admissions:certificate') + '?limit=5&offset=5'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'count': 10,
            'first': 'http://testserver/v1/admissions/certificate?limit=5',
            'last': None,
            'next': None,
            'previous': 'http://testserver/v1/admissions/certificate?limit=5',
            'results': [{
                'id': model['certificate'].id,
                'name': model['certificate'].name,
                'slug': model['certificate'].slug,
                'logo': model['certificate'].logo,
                'description': model['certificate'].description,
            } for model in models if model['certificate'].id > 5]
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_certificate_dict(), [{
            **self.model_to_dict(model, 'certificate'),
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_with_data_with_pagination_after_last_five(self):
        """Test /certificate without auth"""
        base = self.generate_models(authenticate=True)
        models = [self.generate_models(certificate=True, models=base) for _ in range(0, 10)]
        url = reverse_lazy('admissions:certificate') + '?limit=5&offset=10'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'count': 10,
            'first': 'http://testserver/v1/admissions/certificate?limit=5',
            'last': None,
            'next': None,
            'previous': 'http://testserver/v1/admissions/certificate?limit=5&offset=5',
            'results': [],
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_certificate_dict(), [{
            **self.model_to_dict(model, 'certificate'),
        } for model in models])

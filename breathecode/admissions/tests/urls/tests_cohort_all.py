"""
Test /cohort/all
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

class CohortAllTestSuite(AdmissionsTestCase):
    """Test /cohort/all"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_without_auth(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_without_data(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_cohort_but_without_profile_academy(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        self.generate_models(authenticate=True, cohort=True)
        model_dict = self.remove_dinamics_fields(self.cohort.__dict__)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_bad_get_academy(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        model_dict = self.remove_dinamics_fields(self.cohort.__dict__)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?academy=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_academy(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        model_dict = self.remove_dinamics_fields(self.cohort.__dict__)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?academy={self.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', self.cohort.kickoff_date.isoformat()),
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'language': self.cohort.language,
            'certificate': {
                'id': self.cohort.certificate.id,
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
                'id': self.cohort.academy.id,
                'slug': self.cohort.academy.slug,
                'name': self.cohort.academy.name,
                'country': {
                    'code': self.cohort.academy.country.code,
                    'name': self.cohort.academy.country.name,
                },
                'city': {
                    'name': self.cohort.academy.city.name,
                },
                'logo_url': self.cohort.academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_bad_get_location(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        model_dict = self.remove_dinamics_fields(self.cohort.__dict__)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_location(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        model_dict = self.remove_dinamics_fields(self.cohort.__dict__)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location={self.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', self.cohort.kickoff_date.isoformat()),
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'language': self.cohort.language,
            'certificate': {
                'id': self.cohort.certificate.id,
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
                'id': self.cohort.academy.id,
                'slug': self.cohort.academy.slug,
                'name': self.cohort.academy.name,
                'country': {
                    'code': self.cohort.academy.country.code,
                    'name': self.cohort.academy.country.name,
                },
                'city': {
                    'name': self.cohort.academy.city.name,
                },
                'logo_url': self.cohort.academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_location_with_comma(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        model_dict = self.remove_dinamics_fields(self.cohort.__dict__)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location={self.academy.slug},they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', self.cohort.kickoff_date.isoformat()),
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'language': self.cohort.language,
            'certificate': {
                'id': self.cohort.certificate.id,
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
                'id': self.cohort.academy.id,
                'slug': self.cohort.academy.slug,
                'name': self.cohort.academy.name,
                'country': {
                    'code': self.cohort.academy.country.code,
                    'name': self.cohort.academy.country.name,
                },
                'city': {
                    'name': self.cohort.academy.city.name,
                },
                'logo_url': self.cohort.academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_upcoming_false(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        model_dict = self.remove_dinamics_fields(self.cohort.__dict__)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=false'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', self.cohort.kickoff_date.isoformat()),
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'language': self.cohort.language,
            'certificate': {
                'id': self.cohort.certificate.id,
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
                'id': self.cohort.academy.id,
                'slug': self.cohort.academy.slug,
                'name': self.cohort.academy.name,
                'country': {
                    'code': self.cohort.academy.country.code,
                    'name': self.cohort.academy.country.name,
                },
                'city': {
                    'name': self.cohort.academy.city.name,
                },
                'logo_url': self.cohort.academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_upcoming_true_without_current_data(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        model_dict = self.remove_dinamics_fields(self.cohort.__dict__)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data_with_get_upcoming_true_with_current_data(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            impossible_kickoff_date=True)
        model_dict = self.get_cohort_dict(1)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': f'{self.cohort.kickoff_date.isoformat()}Z',
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'language': self.cohort.language,
            'certificate': {
                'id': self.cohort.certificate.id,
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
                'id': self.cohort.academy.id,
                'slug': self.cohort.academy.slug,
                'name': self.cohort.academy.name,
                'country': {
                    'code': self.cohort.academy.country.code,
                    'name': self.cohort.academy.country.name,
                },
                'city': {
                    'name': self.cohort.academy.city.name,
                },
                'logo_url': self.cohort.academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_all_with_data(self):
        """Test /cohort/all without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        model_dict = self.remove_dinamics_fields(self.cohort.__dict__)
        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', self.cohort.kickoff_date.isoformat()),
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'language': self.cohort.language,
            'certificate': {
                'id': self.cohort.certificate.id,
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
                'id': self.cohort.academy.id,
                'slug': self.cohort.academy.slug,
                'name': self.cohort.academy.name,
                'country': {
                    'code': self.cohort.academy.country.code,
                    'name': self.cohort.academy.country.name,
                },
                'city': {
                    'name': self.cohort.academy.city.name,
                },
                'logo_url': self.cohort.academy.logo_url,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

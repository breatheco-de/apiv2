"""
Test /cohort
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
from ..utils import GenerateModels

class CohortTestSuite(AdmissionsTestCase):
    """Test /cohort"""

    def test_cohort_without_auth(self):
        """Test /cohort without auth"""
        url = reverse_lazy('admissions:cohort')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cohort_without_data(self):
        """Test /cohort without auth"""
        url = reverse_lazy('admissions:cohort')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_data(self):
        """Test /cohort without auth"""
        url = reverse_lazy('admissions:cohort')
        self.generate_models(authenticate=True, cohort=True)
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', self.cohort.kickoff_date.isoformat()),
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
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

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_put_without_id(self):
        """Test /cohort without auth"""
        url = reverse_lazy('admissions:cohort')
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'details': 'Missing cohort_id', 'status_code': 400})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_data_with_upcoming_false(self):
        """Test /cohort without auth"""
        self.generate_models(authenticate=True, cohort=True)
        base_url = reverse_lazy('admissions:cohort')
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
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
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

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_data_with_upcoming_true_without_data(self):
        """Test /cohort without auth"""
        self.generate_models(authenticate=True, cohort=True)
        base_url = reverse_lazy('admissions:cohort')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_data_with_upcoming_true(self):
        """Test /cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, impossible_kickoff_date=True)
        base_url = reverse_lazy('admissions:cohort')
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
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
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

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_data_with_bad_academy(self):
        """Test /cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            impossible_kickoff_date=True)
        base_url = reverse_lazy('admissions:cohort')
        url = f'{base_url}?academy=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_data_with_academy(self):
        """Test /cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            impossible_kickoff_date=True)
        base_url = reverse_lazy('admissions:cohort')
        url = f'{base_url}?academy={self.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': f'{self.cohort.kickoff_date.isoformat()}Z',
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
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

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_data_with_academy_with_comma(self):
        """Test /cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            impossible_kickoff_date=True)
        base_url = reverse_lazy('admissions:cohort')
        url = f'{base_url}?academy={self.academy.slug},they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': f'{self.cohort.kickoff_date.isoformat()}Z',
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
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

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_ten_datas_with_academy_with_comma(self):
        """Test /cohort without auth"""
        models = [GenerateModels(authenticate=True, cohort=True, profile_academy=True,
            impossible_kickoff_date=True) for index in range(0, 10)]
        self.client.force_authenticate(user=models[0].user)
        base_url = reverse_lazy('admissions:cohort')
        params = ','.join([model.academy.slug for model in models])
        url = f'{base_url}?academy={params}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.cohort.id,
            'slug': model.cohort.slug,
            'name': model.cohort.name,
            'kickoff_date': f'{model.cohort.kickoff_date.isoformat()}Z',
            'ending_date': model.cohort.ending_date,
            'stage': model.cohort.stage,
            'certificate': {
                'slug': model.cohort.certificate.slug,
                'name': model.cohort.certificate.name,
                'description': model.cohort.certificate.description,
                'logo': model.cohort.certificate.logo,
            },
            'academy': {
                'slug': model.cohort.academy.slug,
                'name': model.cohort.academy.name,
                'country': {
                    'code': model.cohort.academy.country.code,
                    'name': model.cohort.academy.country.name,
                },
                'city': {
                    'name': model.cohort.academy.city.name,
                },
                'logo_url': model.cohort.academy.logo_url,
            },
        } for model in models]
        json.sort(key=lambda x: x['id'])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_data_with_bad_location(self):
        """Test /cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            impossible_kickoff_date=True)
        base_url = reverse_lazy('admissions:cohort')
        url = f'{base_url}?location=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_data_with_location(self):
        """Test /cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            impossible_kickoff_date=True)
        base_url = reverse_lazy('admissions:cohort')
        url = f'{base_url}?location={self.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': f'{self.cohort.kickoff_date.isoformat()}Z',
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
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

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_data_with_location_with_comma(self):
        """Test /cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            impossible_kickoff_date=True)
        base_url = reverse_lazy('admissions:cohort')
        url = f'{base_url}?location={self.academy.slug},they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort.id,
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': f'{self.cohort.kickoff_date.isoformat()}Z',
            'ending_date': self.cohort.ending_date,
            'stage': self.cohort.stage,
            'certificate': {
                'slug': self.cohort.certificate.slug,
                'name': self.cohort.certificate.name,
                'description': self.cohort.certificate.description,
                'logo': self.cohort.certificate.logo,
            },
            'academy': {
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

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_with_ten_datas_with_location_with_comma(self):
        """Test /cohort without auth"""
        # self.generate_models(authenticate=True, cohort=True, profile_academy=True,
        #     impossible_kickoff_date=True)
        models = [GenerateModels(authenticate=True, cohort=True, profile_academy=True,
            impossible_kickoff_date=True) for index in range(0, 10)]
        # models[0].authenticate()
        self.client.force_authenticate(user=models[0].user)
        base_url = reverse_lazy('admissions:cohort')
        params = ','.join([model.academy.slug for model in models])
        url = f'{base_url}?location={params}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model.cohort.id,
            'slug': model.cohort.slug,
            'name': model.cohort.name,
            'kickoff_date': f'{model.cohort.kickoff_date.isoformat()}Z',
            'ending_date': model.cohort.ending_date,
            'stage': model.cohort.stage,
            'certificate': {
                'slug': model.cohort.certificate.slug,
                'name': model.cohort.certificate.name,
                'description': model.cohort.certificate.description,
                'logo': model.cohort.certificate.logo,
            },
            'academy': {
                'slug': model.cohort.academy.slug,
                'name': model.cohort.academy.name,
                'country': {
                    'code': model.cohort.academy.country.code,
                    'name': model.cohort.academy.country.name,
                },
                'city': {
                    'name': model.cohort.academy.city.name,
                },
                'logo_url': model.cohort.academy.logo_url,
            },
        } for model in models]
        json.sort(key=lambda x: x['id'])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

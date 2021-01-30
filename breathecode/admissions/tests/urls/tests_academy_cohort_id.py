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
from ..mixins.new_admissions_test_case import AdmissionsTestCase

class AcademyCohortTestSuite(AdmissionsTestCase):
    """Test /cohort"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_without_auth(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 1})
        response = self.client.put(url, {})
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_put_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 1})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: crud_cohort for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_put_with_id_without_certificate(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            capability='crud_cohort', role='potato')
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'certificate': ['This field is required.']})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_put_without_cohort(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 99999})
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_cohort', role='potato', certificate=True)
        data = {
            'certificate': model['certificate'].id
        }
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'status_code': 500, 'details': 'Specified cohort not be found'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), self.remove_dinamics_fields(model['cohort'].__dict__))

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_put(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 1})
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_cohort', role='potato', certificate=True)
        data = {
            'certificate': model['certificate'].id
        }
        response = self.client.put(url, data)
        json = response.json()

        expected = {
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
            'ending_date': model['cohort'].ending_date,
            'current_day': model['cohort'].current_day,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'certificate': model['cohort'].certificate.id,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), self.remove_dinamics_fields(model['cohort'].__dict__))

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_put_with_id_with_data_in_body(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            capability='crud_cohort', role='potato', certificate=True)
        model_dict = self.get_cohort_dict(1)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'certificate': model['certificate'].id,
            'slug': 'they-killed-kenny',
            'name': 'They killed kenny',
            'current_day': model['cohort'].current_day + 1,
            'language': 'es',
        }
        model_dict.update(data)
        model_dict['certificate_id'] = model_dict['certificate']
        del model_dict['certificate']
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'id': model['cohort'].id,
            'slug': data['slug'],
            'name': data['name'],
            'kickoff_date': re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
            'ending_date': model['cohort'].ending_date,
            'current_day': data['current_day'],
            'stage': model['cohort'].stage,
            'language': data['language'],
            'certificate': model['cohort'].certificate.id,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_get_with_id(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            capability='read_cohort', role='potato', certificate=True)
        model_dict = self.remove_dinamics_fields(model['cohort'].__dict__)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        response = self.client.get(url)
        json = response.json()
        expected = {
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
            'ending_date': model['cohort'].ending_date,
            'stage': model['cohort'].stage,
            'language': model['cohort'].language,
            'certificate': {
                'id': model['cohort'].certificate.id,
                'slug': model['cohort'].certificate.slug,
                'name': model['cohort'].certificate.name,
                'description': model['cohort'].certificate.description,
                'logo': model['cohort'].certificate.logo,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
                'logo_url': model['cohort'].academy.logo_url,
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_get_with_bad_slug(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            capability='read_cohort', role='potato', certificate=True)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 'they-killed-kenny'})
        response = self.client.get(url)

        self.assertEqual(response.data, None)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_get_with_slug(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True,
            capability='read_cohort', role='potato', certificate=True)
        model_dict = self.remove_dinamics_fields(model['cohort'].__dict__)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].slug})
        response = self.client.get(url)
        json = response.json()
        expected = {
            'id': model['cohort'].id,
            'slug': model['cohort'].slug,
            'name': model['cohort'].name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
            'ending_date': model['cohort'].ending_date,
            'language': model['cohort'].language,
            'stage': model['cohort'].stage,
            'certificate': {
                'id': model['cohort'].certificate.id,
                'slug': model['cohort'].certificate.slug,
                'name': model['cohort'].certificate.name,
                'description': model['cohort'].certificate.description,
                'logo': model['cohort'].certificate.logo,
            },
            'academy': {
                'id': model['cohort'].academy.id,
                'slug': model['cohort'].academy.slug,
                'name': model['cohort'].academy.name,
                'country': model['cohort'].academy.country,
                'city': model['cohort'].academy.city,
                'logo_url': model['cohort'].academy.logo_url,
                'country': {
                    'code': model['cohort'].academy.country.code,
                    'name': model['cohort'].academy.country.name,
                },
                'city': {
                    'name': model['cohort'].academy.city.name,
                },
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 1)
        self.assertEqual(self.get_cohort_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_delete_with_bad_id(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            capability='read_cohort', role='potato', certificate=True, cohort_user=True)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': 0})
        self.assertEqual(self.count_cohort_user(), 1)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.count_cohort_stage(model['cohort'].id), 'INACTIVE')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_delete_with_id(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            capability='crud_cohort', role='potato', certificate=True, cohort_user=True)
        url = reverse_lazy('admissions:academy_cohort_id', kwargs={'cohort_id': model['cohort'].id})
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.count_cohort_stage(model['cohort'].id), 'INACTIVE')
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.count_cohort_user(), 0)
        self.assertEqual(self.count_cohort_stage(model['cohort'].id), 'DELETED')

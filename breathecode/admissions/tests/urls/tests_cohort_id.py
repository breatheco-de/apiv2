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

class CohortTestSuite(AdmissionsTestCase):
    """Test /cohort"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_without_auth(self):
        """Test /cohort/:id without auth"""
        url = reverse_lazy('admissions:cohort_id', kwargs={'cohort_id': 1})
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
    def test_cohort_id_put_with_bad_id(self):
        """Test /cohort/:id without auth"""
        url = reverse_lazy('admissions:cohort_id', kwargs={'cohort_id': 1})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'status_code': 500, 'details': 'Specified cohort not be found'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_put_with_id_but_without_profile_academy(self):
        """Test /cohort/:id without auth"""
        self.generate_models(authenticate=True, cohort=True)
        url = reverse_lazy('admissions:cohort_id', kwargs={'cohort_id': self.cohort.id})
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'status_code': 500, 'details': 'Specified cohort not be found'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_put_with_id_without_certificate(self):
        """Test /cohort/:id without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id', kwargs={'cohort_id': self.cohort.id})
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'certificate': ['This field is required.']})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_put_with_id(self):
        """Test /cohort/:id without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id', kwargs={'cohort_id': self.cohort.id})
        data = {
            'certificate': self.certificate.id
        }
        response = self.client.put(url, data)
        json = response.json()
        expected = {
            'slug': self.cohort.slug,
            'name': self.cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', 'Z', self.cohort.kickoff_date.isoformat()),
            'ending_date': self.cohort.ending_date,
            'current_day': self.cohort.current_day,
            'stage': self.cohort.stage,
            'language': self.cohort.language,
            'certificate': self.cohort.certificate.id,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_get_with_id(self):
        """Test /cohort/:id without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id', kwargs={'cohort_id': self.cohort.id})
        response = self.client.get(url)
        json = response.json()
        expected = {
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
                'country': self.cohort.academy.country,
                'city': self.cohort.academy.city,
                'logo_url': self.cohort.academy.logo_url,
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_get_with_bad_slug(self):
        """Test /cohort/:id without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id', kwargs={'cohort_id': 'they-killed-kenny'})
        response = self.client.get(url)
        # json = response.json()

        self.assertEqual(response.data, None)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_get_with_slug(self):
        """Test /cohort/:id without auth"""
        self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id', kwargs={'cohort_id': self.cohort.slug})
        response = self.client.get(url)
        json = response.json()
        expected = {
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
                'country': self.cohort.academy.country,
                'city': self.cohort.academy.city,
                'logo_url': self.cohort.academy.logo_url,
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

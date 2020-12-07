"""
Test /academy/cohort
"""
import re
from datetime import datetime
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

class AcademyCohortTestSuite(AdmissionsTestCase):
    """Test /academy/cohort"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_post_without_authorization(self):
        """Test /academy/cohort without auth"""
        # self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
        #     cohort_user=True)
        url = reverse_lazy('admissions:academy_cohort')
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_post_without_profile_academy(self):
        """Test /academy/cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True)
        url = reverse_lazy('admissions:academy_cohort')
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'detail': 'Specified academy not be found',
            'status_code': status.HTTP_403_FORBIDDEN
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_post_dont_accept_academy_param(self):
        """Test /academy/cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'academy':  999,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'detail': "academy and academy_id field is not allowed",
            'status_code': 400
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_post_without_certificate(self):
        """Test /academy/cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        url = reverse_lazy('admissions:academy_cohort')
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'certificate field is missing', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_post_with_bad_fields(self):
        """Test /academy/cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            certificate=True)
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'certificate':  self.certificate.id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'slug': ['This field is required.'],
            'name': ['This field is required.'],
            'kickoff_date': ['This field is required.']
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_post_with_bad_certificate(self):
        """Test /academy/cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'certificate':  999,
            'slug':  'they-killed-kenny',
            'name':  'They killed kenny',
            'kickoff_date':  datetime.today().isoformat(),
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'specified certificate not be found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_post_with_bad_current_day(self):
        """Test /academy/cohort without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            certificate=True)
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'certificate':  self.certificate.id,
            'current_day':  999,
            'slug':  'they-killed-kenny',
            'name':  'They killed kenny',
            'kickoff_date':  datetime.today().isoformat(),
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'current_day field is not allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_post(self):
        """Test /academy/cohort without auth"""
        self.assertEqual(self.count_cohort(), 0)
        self.generate_models(authenticate=True, user=True, profile_academy=True,
            certificate=True)
        self.assertEqual(self.count_cohort(), 1)
        models_dict = self.all_cohort_dict()
        url = reverse_lazy('admissions:academy_cohort')
        data = {
            'certificate':  self.certificate.id,
            'slug':  'they-killed-kenny',
            'name':  'They killed kenny',
            'kickoff_date':  datetime.today().isoformat(),
        }
        response = self.client.post(url, data)
        json = response.json()
        cohort = self.get_cohort(2)
        assert cohort is not None
        expected = {
            'id': cohort.id,
            'slug': cohort.slug,
            'name': cohort.name,
            'kickoff_date': re.sub(r'\+00:00$', '', cohort.kickoff_date.isoformat()),
            'current_day': cohort.current_day,
            'academy': {
                'id': cohort.academy.id,
                'slug': cohort.academy.slug,
                'name': cohort.academy.name,
                'street_address': cohort.academy.street_address,
                'country': cohort.academy.country.code,
                'city': cohort.academy.city.id,
            },
            'certificate': {
                'id': cohort.certificate.id,
                'name': cohort.certificate.name,
                'slug': cohort.certificate.slug,
            },
            'ending_date': cohort.ending_date,
            'stage': cohort.stage,
            'language': cohort.language,
            'created_at': re.sub(r'\+00:00$', 'Z', cohort.created_at.isoformat()),
            'updated_at': re.sub(r'\+00:00$', 'Z', cohort.updated_at.isoformat()),
        }

        del data['kickoff_date']
        cohort_two = cohort.__dict__.copy()
        cohort_two.update(data)
        cohort_two['certificate_id'] = cohort_two['certificate']
        del cohort_two['certificate']
        models_dict.append(self.remove_dinamics_fields(cohort_two))

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_dict(), models_dict)

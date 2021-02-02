"""
Test /cohort/:id/user
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

class CohortIdUserIdTestSuite(AdmissionsTestCase):
    """Test /cohort/:id/user"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_bad_cohort_id(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': 999})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'Missing cohort_id or user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_bad_user(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {
            'user': 999
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'invalid user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_without_user(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'Missing cohort_id or user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_without_profile_academy(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {
            'user':  self.user.id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'Specified cohort not be found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        models_dict = self.all_cohort_user_dict()
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {
            'user':  self.user.id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'id': 1,
            'role': 'STUDENT',
            'user': {
                'id': self.user.id,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'email': self.user.email,
            },
            'cohort': {
                'id': self.cohort.id,
                'slug': self.cohort.slug,
                'name': self.cohort.name,
                'kickoff_date': re.sub(
                    r'\+00:00$', 'Z',
                    self.cohort.kickoff_date.isoformat()
                ),
                'current_day': self.cohort.current_day,
                'academy': {
                    'id': self.cohort.academy.id,
                    'name': self.cohort.academy.name,
                    'slug': self.cohort.academy.slug,
                    'country': self.cohort.academy.country.code,
                    'city': self.cohort.academy.city.id,
                    'street_address': self.cohort.academy.street_address,
                },
                'certificate': {
                    'id': self.cohort.certificate.id,
                    'name': self.cohort.certificate.name,
                    'slug': self.cohort.certificate.slug,
                },
                'ending_date': self.cohort.ending_date,
                'stage': self.cohort.stage,
                'language': self.cohort.language,
                'created_at': re.sub(r'\+00:00$', 'Z', self.cohort.created_at.isoformat()),
                'updated_at': re.sub(r'\+00:00$', 'Z', self.cohort.updated_at.isoformat()),
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cohort_user = self.get_cohort_user(1)
        cohort_user_two = cohort_user.__dict__.copy()
        cohort_user_two.update(data)
        cohort_user_two['user_id'] = cohort_user_two['user']
        cohort_user_two['cohort_id'] = self.cohort.id
        del cohort_user_two['user']
        models_dict.append(self.remove_dinamics_fields(cohort_user_two))

        self.assertEqual(self.all_cohort_user_dict(), models_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_two_cohort_with_the_same_certificate(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, cohort_two=True, user=True,
            profile_academy=True, cohort_user=True, user_two=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort_two.id})
        data = {
            'user':  self.user.id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'status_code': 400, 'detail': 'This student is already in another cohort for the same certificate, please mark him/her hi educational status on this prior cohort as POSTPONED before cotinuing'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_twice(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {
            'user':  self.user.id,
        }
        self.client.post(url, data)
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'That user already exists in this cohort', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_one_teacher(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        models_dict = self.all_cohort_user_dict()
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {
            'user':  self.user.id,
            'role': 'TEACHER'
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'id': 1,
            'role': 'TEACHER',
            'user': {
                'id': self.user.id,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'email': self.user.email,
            },
            'cohort': {
                'id': self.cohort.id,
                'slug': self.cohort.slug,
                'name': self.cohort.name,
                'kickoff_date': re.sub(
                    r'\+00:00$', 'Z',
                    self.cohort.kickoff_date.isoformat()
                ),
                'current_day': self.cohort.current_day,
                'academy': {
                    'id': self.cohort.academy.id,
                    'name': self.cohort.academy.name,
                    'slug': self.cohort.academy.slug,
                    'country': self.cohort.academy.country.code,
                    'city': self.cohort.academy.city.id,
                    'street_address': self.cohort.academy.street_address,
                },
                'certificate': {
                    'id': self.cohort.certificate.id,
                    'name': self.cohort.certificate.name,
                    'slug': self.cohort.certificate.slug,
                },
                'ending_date': self.cohort.ending_date,
                'stage': self.cohort.stage,
                'language': self.cohort.language,
                'created_at': re.sub(r'\+00:00$', 'Z', self.cohort.created_at.isoformat()),
                'updated_at': re.sub(r'\+00:00$', 'Z', self.cohort.updated_at.isoformat()),
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cohort_user = self.get_cohort_user(1)
        cohort_user_two = cohort_user.__dict__.copy()
        cohort_user_two.update(data)
        cohort_user_two['user_id'] = cohort_user_two['user']
        cohort_user_two['cohort_id'] = self.cohort.id
        del cohort_user_two['user']
        models_dict.append(self.remove_dinamics_fields(cohort_user_two))

        self.assertEqual(self.all_cohort_user_dict(), models_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_two_teacher(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, user_two=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {
            'user':  self.user.id,
            'role': 'TEACHER'
        }
        self.client.post(url, data)

        data = {
            'user':  self.user_two.id,
            'role': 'TEACHER'
        }
        response = self.client.post(url, data)
        json = response.json()
        
        # TODO: If you update the main teacher if should not give this error, only when you POST.
        expected = {
            'status_code': 400,
            'detail': 'There can only be one main instructor in a cohort',
        }
        print(json)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_unsuccess_task(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            task=True, task_status='PENDING', task_type='PROJECT')
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {
            'user':  self.user.id,
            'educational_status': 'GRADUATED',
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'status_code': 400,
            'detail': 'User has tasks with status pending the educational status cannot be GRADUATED',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_unsuccess_finantial_status(self):
        """Test /cohort/:id/user without auth"""
        self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': self.cohort.id})
        data = {
            'user':  self.user.id,
            'educational_status': 'GRADUATED',
            'finantial_status': 'LATE',
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'status_code': 400,
            'detail': 'Cannot be marked as `GRADUATED` if its financial status is `LATE`',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

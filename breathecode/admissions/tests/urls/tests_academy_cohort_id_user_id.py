"""
Test /cohort/user
"""
import re
from random import choice
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

class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""

    """
    🔽🔽🔽 Auth
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_user__without_auth(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        response = self.client.post(url, {})
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 Post method
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_user__post(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, cohort=True, user=True,
            profile_academy=True, capability='crud_cohort', role='potato')

        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        data = {
            'user':  model['user'].id,
            'cohort':  model['cohort'].id,
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'id': 1,
            'role': 'STUDENT',
            'user': {
                'id': model['user'].id,
                'first_name': model['user'].first_name,
                'last_name': model['user'].last_name,
                'email': model['user'].email,
            },
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name,
                'never_ends': False,
                'kickoff_date': re.sub(
                    r'\+00:00$', 'Z',
                    model['cohort'].kickoff_date.isoformat()
                ),
                'current_day': model['cohort'].current_day,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'syllabus': None,
                'ending_date': model['cohort'].ending_date,
                'stage': model['cohort'].stage,
                'language': model['cohort'].language,
                'created_at': re.sub(r'\+00:00$', 'Z', model['cohort'].created_at.isoformat()),
                'updated_at': re.sub(r'\+00:00$', 'Z', model['cohort'].updated_at.isoformat()),
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'STUDENT',
            'user_id': 1,
        }])

    """
    🔽🔽🔽 Add the same teacher to two cohors
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_user__post__same_teacher_in_two_cohorts(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        models = [self.generate_models(authenticate=True, user=True, cohort=True,
            profile_academy=True, capability='crud_cohort', role='staff')]

        base = models[0].copy()
        del base['cohort']

        models = models + [self.generate_models(cohort=True, models=base)]
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        data = {
            'user':  1,
            'cohort':  1,
            'role': 'TEACHER',
        }
        response = self.client.post(url, data, format='json')

        data = {
            'user':  1,
            'cohort':  2,
            'role': 'TEACHER',
        }
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 2, 'user_id': 1})
        response = self.client.post(url, data, format='json')
        json = response.json()
        model = models[1]
        expected = {
            'id': 2,
            'role': 'TEACHER',
            'user': {
                'id': model['user'].id,
                'first_name': model['user'].first_name,
                'last_name': model['user'].last_name,
                'email': model['user'].email,
            },
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name,
                'never_ends': False,
                'kickoff_date': re.sub(
                    r'\+00:00$', 'Z',
                    model['cohort'].kickoff_date.isoformat()
                ),
                'current_day': model['cohort'].current_day,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'syllabus': None,
                'ending_date': model['cohort'].ending_date,
                'stage': model['cohort'].stage,
                'language': model['cohort'].language,
                'created_at': re.sub(r'\+00:00$', 'Z', model['cohort'].created_at.isoformat()),
                'updated_at': re.sub(r'\+00:00$', 'Z', model['cohort'].updated_at.isoformat()),
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'TEACHER',
            'user_id': 1,
        }, {
            'cohort_id': 2,
            'educational_status': None,
            'finantial_status': None,
            'id': 2,
            'role': 'TEACHER',
            'user_id': 1,
        }])

    """
    🔽🔽🔽 Put
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_user__put(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        model = self.generate_models(authenticate=True, cohort_user=True,
            profile_academy=True, capability='crud_cohort', role='potato')
        data = {
            'id': model['cohort_user'].id,
            'user': 1,
            'cohort': 1,
        }
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'id': 1,
            'role': 'STUDENT',
            'educational_status': None,
            'finantial_status': None,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_user_dict(), [{
            **self.model_to_dict(model, 'cohort_user'),
            'role': 'STUDENT',
        }])

    """
    🔽🔽🔽 Put teacher
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_user__put__teacher_that_is_not_staff(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        model = self.generate_models(authenticate=True, cohort_user=True,
            profile_academy=True, capability='crud_cohort', role='potato')
        data = {
            'id': model['cohort_user'].id,
            'role': 'TEACHER',
            'user': 1,
            'cohort': 1,
        }
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'The user must be staff member to this academy before it can be a teacher',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(), [{
            **self.model_to_dict(model, 'cohort_user'),
            'role': 'STUDENT',
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_cohort_user__put__teacher(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        model = self.generate_models(authenticate=True, cohort_user=True,
            profile_academy=True, capability='crud_cohort', role='staff')
        data = {
            'id': model['cohort_user'].id,
            'role': 'TEACHER',
            'user': 1,
            'cohort': 1,
        }
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'id': 1,
            'role': 'TEACHER',
            'educational_status': None,
            'finantial_status': None
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_user_dict(), [{
            **self.model_to_dict(model, 'cohort_user'),
            'role': 'TEACHER',
        }])
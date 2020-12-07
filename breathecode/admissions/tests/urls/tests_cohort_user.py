"""
Test /cohort/user
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

class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""

    def test_cohort_user_without_auth(self):
        """Test /cohort/user without auth"""
        url = reverse_lazy('admissions:cohort_user')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cohort_user_without_data(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:cohort_user')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        url = reverse_lazy('admissions:cohort_user')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'role': self.cohort_user.role,
            'finantial_status': self.cohort_user.finantial_status,
            'educational_status': self.cohort_user.educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', self.cohort_user.created_at.isoformat()),
            'cohort': {
                'id': self.cohort_user.cohort.id,
                'kickoff_date': self.cohort_user.cohort.kickoff_date,
                'name': self.cohort_user.cohort.name,
                'slug': self.cohort_user.cohort.slug,
                'stage': self.cohort_user.cohort.stage,
            },
            'user': {
                'id': self.cohort_user.user.id,
                'first_name': self.cohort_user.user.first_name,
                'last_name': self.cohort_user.user.last_name,
                'email': self.cohort_user.user.email,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_bad_roles(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?roles=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_roles(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?roles={self.cohort_user.role}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'role': self.cohort_user.role,
            'finantial_status': self.cohort_user.finantial_status,
            'educational_status': self.cohort_user.educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', self.cohort_user.created_at.isoformat()),
            'cohort': {
                'id': self.cohort_user.cohort.id,
                'kickoff_date': self.cohort_user.cohort.kickoff_date,
                'name': self.cohort_user.cohort.name,
                'slug': self.cohort_user.cohort.slug,
                'stage': self.cohort_user.cohort.stage,
            },
            'user': {
                'id': self.cohort_user.user.id,
                'first_name': self.cohort_user.user.first_name,
                'last_name': self.cohort_user.user.last_name,
                'email': self.cohort_user.user.email,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_roles_with_comma(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?roles={self.cohort_user.role},they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort_user.id,
            'role': self.cohort_user.role,
            'finantial_status': self.cohort_user.finantial_status,
            'educational_status': self.cohort_user.educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', self.cohort_user.created_at.isoformat()),
            'user': {
                'id': self.cohort_user.user.id,
                'first_name': self.cohort_user.user.first_name,
                'last_name': self.cohort_user.user.last_name,
                'email': self.cohort_user.user.email,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_bad_finantial_status(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?finantial_status=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_finantial_status(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True, finantial_status='LATE')
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?finantial_status={self.cohort_user.finantial_status}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'role': self.cohort_user.role,
            'finantial_status': self.cohort_user.finantial_status,
            'educational_status': self.cohort_user.educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', self.cohort_user.created_at.isoformat()),
            'cohort': {
                'id': self.cohort_user.cohort.id,
                'kickoff_date': self.cohort_user.cohort.kickoff_date,
                'name': self.cohort_user.cohort.name,
                'slug': self.cohort_user.cohort.slug,
                'stage': self.cohort_user.cohort.stage,
            },
            'user': {
                'id': self.cohort_user.user.id,
                'first_name': self.cohort_user.user.first_name,
                'last_name': self.cohort_user.user.last_name,
                'email': self.cohort_user.user.email,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_finantial_status_with_comma(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True, finantial_status='LATE')
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?finantial_status={self.cohort_user.finantial_status},they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort_user.id,
            'role': self.cohort_user.role,
            'finantial_status': self.cohort_user.finantial_status,
            'educational_status': self.cohort_user.educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', self.cohort_user.created_at.isoformat()),
            'user': {
                'id': self.cohort_user.user.id,
                'first_name': self.cohort_user.user.first_name,
                'last_name': self.cohort_user.user.last_name,
                'email': self.cohort_user.user.email,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_bad_educational_status(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?educational_status=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_educational_status(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True, educational_status='GRADUATED')
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?educational_status={self.cohort_user.educational_status}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort_user.id,
            'role': self.cohort_user.role,
            'finantial_status': self.cohort_user.finantial_status,
            'educational_status': self.cohort_user.educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', self.cohort_user.created_at.isoformat()),
            'user': {
                'id': self.cohort_user.user.id,
                'first_name': self.cohort_user.user.first_name,
                'last_name': self.cohort_user.user.last_name,
                'email': self.cohort_user.user.email,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_educational_status_with_comma(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True, educational_status='GRADUATED')
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = (f'{base_url}?educational_status={self.cohort_user.educational_status},'
            'they-killed-kenny')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort_user.id,
            'role': self.cohort_user.role,
            'finantial_status': self.cohort_user.finantial_status,
            'educational_status': self.cohort_user.educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', self.cohort_user.created_at.isoformat()),
            'user': {
                'id': self.cohort_user.user.id,
                'first_name': self.cohort_user.user.first_name,
                'last_name': self.cohort_user.user.last_name,
                'email': self.cohort_user.user.email,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_bad_academy(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?academy=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_academy(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True, educational_status='GRADUATED')
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?academy={self.cohort_user.cohort.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort_user.id,
            'role': self.cohort_user.role,
            'finantial_status': self.cohort_user.finantial_status,
            'educational_status': self.cohort_user.educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', self.cohort_user.created_at.isoformat()),
            'user': {
                'id': self.cohort_user.user.id,
                'first_name': self.cohort_user.user.first_name,
                'last_name': self.cohort_user.user.last_name,
                'email': self.cohort_user.user.email,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_academy_with_comma(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True, educational_status='GRADUATED')
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?academy={self.cohort_user.cohort.academy.slug},they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort_user.id,
            'role': self.cohort_user.role,
            'finantial_status': self.cohort_user.finantial_status,
            'educational_status': self.cohort_user.educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', self.cohort_user.created_at.isoformat()),
            'user': {
                'id': self.cohort_user.user.id,
                'first_name': self.cohort_user.user.first_name,
                'last_name': self.cohort_user.user.last_name,
                'email': self.cohort_user.user.email,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_bad_cohorts(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?cohorts=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_with_data_with_cohorts(self):
        """Test /cohort/user without auth"""
        self.generate_models(authenticate=True, cohort_user=True, educational_status='GRADUATED')
        model_dict = self.remove_dinamics_fields(self.cohort_user.__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?cohorts={self.cohort_user.cohort.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': self.cohort_user.id,
            'role': self.cohort_user.role,
            'finantial_status': self.cohort_user.finantial_status,
            'educational_status': self.cohort_user.educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', self.cohort_user.created_at.isoformat()),
            'user': {
                'id': self.cohort_user.user.id,
                'first_name': self.cohort_user.user.first_name,
                'last_name': self.cohort_user.user.last_name,
                'email': self.cohort_user.user.email,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_user_put_without_id(self):
        """Test /cohort/user without auth"""
        url = reverse_lazy('admissions:cohort_user')
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'status_code': 400, 'details': 'Missing cohort_id or user_id'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

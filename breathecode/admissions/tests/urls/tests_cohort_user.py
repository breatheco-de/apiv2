"""
Test /cohort/user
"""
from random import choice
import re
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins import AdmissionsTestCase
from breathecode.admissions.caches import CohortUserCache


def put_serializer(self, cohort_user, cohort, user, profile_academy=None, data={}):
    return {
        'cohort': {
            'ending_date': cohort.ending_date,
            'id': cohort.id,
            'kickoff_date': self.bc.datetime.to_iso_string(cohort.kickoff_date),
            'name': cohort.name,
            'slug': cohort.slug,
            'stage': cohort.stage,
        },
        'created_at': self.bc.datetime.to_iso_string(cohort_user.created_at),
        'educational_status': cohort_user.educational_status,
        'finantial_status': cohort_user.finantial_status,
        'id': cohort_user.id,
        'profile_academy': {
            'email': profile_academy.email,
            'first_name': profile_academy.first_name,
            'id': profile_academy.id,
            'last_name': profile_academy.last_name,
            'phone': profile_academy.phone,
        } if profile_academy else None,
        'role': cohort_user.role,
        'user': {
            'email': user.email,
            'first_name': user.first_name,
            'id': user.id,
            'last_name': user.last_name,
        },
        'watching': cohort_user.watching,
        **data,
    }


class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""

    def test_without_auth(self):
        """Test /cohort/user without auth"""
        url = reverse_lazy('admissions:cohort_user')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_without_data(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:cohort_user')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_with_data(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        url = reverse_lazy('admissions:cohort_user')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'cohort': {
                'id': model['cohort_user'].cohort.id,
                'slug': model['cohort_user'].cohort.slug,
                'name': model['cohort_user'].cohort.name,
                'kickoff_date': re.sub(r'\+00:00$', 'Z',
                                       model['cohort_user'].cohort.kickoff_date.isoformat()),
                'ending_date': model['cohort_user'].cohort.ending_date,
                'stage': model['cohort_user'].cohort.stage,
            },
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
            },
            'profile_academy': None,
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_with_data_with_bad_roles(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
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
    def test_with_data_with_roles(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?roles=' + model['cohort_user'].role
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'cohort': {
                'id': model['cohort_user'].cohort.id,
                'slug': model['cohort_user'].cohort.slug,
                'name': model['cohort_user'].cohort.name,
                'kickoff_date': re.sub(r'\+00:00$', 'Z',
                                       model['cohort_user'].cohort.kickoff_date.isoformat()),
                'ending_date': model['cohort_user'].cohort.ending_date,
                'stage': model['cohort_user'].cohort.stage,
            },
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
            },
            'profile_academy': None,
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_with_data_with_roles_with_comma(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?roles=' + model['cohort_user'].role + ',they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        expected = [{
            'id': model['cohort_user'].id,
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
            },
            'profile_academy': None,
            'cohort': {
                'id': model['cohort_user'].cohort.id,
                'slug': model['cohort_user'].cohort.slug,
                'name': model['cohort_user'].cohort.name,
                'kickoff_date': re.sub(r'\+00:00$', 'Z',
                                       model['cohort_user'].cohort.kickoff_date.isoformat()),
                'ending_date': model['cohort_user'].cohort.ending_date,
                'stage': model['cohort_user'].cohort.stage,
            },
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_with_data_with_bad_finantial_status(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
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
    def test_with_data_with_finantial_status(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'finantial_status': 'LATE'})
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?finantial_status=' + model['cohort_user'].finantial_status
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'cohort': {
                'id': model['cohort_user'].cohort.id,
                'slug': model['cohort_user'].cohort.slug,
                'name': model['cohort_user'].cohort.name,
                'kickoff_date': re.sub(r'\+00:00$', 'Z',
                                       model['cohort_user'].cohort.kickoff_date.isoformat()),
                'ending_date': model['cohort_user'].cohort.ending_date,
                'stage': model['cohort_user'].cohort.stage,
            },
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
            },
            'profile_academy': None,
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_with_data_with_finantial_status_with_comma(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'finantial_status': 'LATE'})
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = (f'{base_url}?finantial_status=' + model['cohort_user'].finantial_status + ',they-killed-kenny')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
            },
            'profile_academy': None,
            'cohort': {
                'id': model['cohort_user'].cohort.id,
                'slug': model['cohort_user'].cohort.slug,
                'name': model['cohort_user'].cohort.name,
                'kickoff_date': re.sub(r'\+00:00$', 'Z',
                                       model['cohort_user'].cohort.kickoff_date.isoformat()),
                'ending_date': model['cohort_user'].cohort.ending_date,
                'stage': model['cohort_user'].cohort.stage,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_with_data_with_bad_educational_status(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
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
    def test_with_data_with_educational_status(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'})
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?educational_status=' + model['cohort_user'].educational_status
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
            },
            'profile_academy': None,
            'cohort': {
                'id': model['cohort_user'].cohort.id,
                'slug': model['cohort_user'].cohort.slug,
                'name': model['cohort_user'].cohort.name,
                'kickoff_date': re.sub(r'\+00:00$', 'Z',
                                       model['cohort_user'].cohort.kickoff_date.isoformat()),
                'ending_date': model['cohort_user'].cohort.ending_date,
                'stage': model['cohort_user'].cohort.stage,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_with_data_with_educational_status_with_comma(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'})
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = (f'{base_url}?educational_status=' + model['cohort_user'].educational_status + ','
               'they-killed-kenny')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
            },
            'profile_academy': None,
            'cohort': {
                'id': model['cohort_user'].cohort.id,
                'slug': model['cohort_user'].cohort.slug,
                'name': model['cohort_user'].cohort.name,
                'kickoff_date': re.sub(r'\+00:00$', 'Z',
                                       model['cohort_user'].cohort.kickoff_date.isoformat()),
                'ending_date': model['cohort_user'].cohort.ending_date,
                'stage': model['cohort_user'].cohort.stage,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_with_data_with_bad_academy(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
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
    def test_with_data_with_academy(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'})
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?academy=' + model['cohort_user'].cohort.academy.slug
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
            },
            'profile_academy': None,
            'cohort': {
                'id': model['cohort_user'].cohort.id,
                'slug': model['cohort_user'].cohort.slug,
                'name': model['cohort_user'].cohort.name,
                'kickoff_date': re.sub(r'\+00:00$', 'Z',
                                       model['cohort_user'].cohort.kickoff_date.isoformat()),
                'ending_date': model['cohort_user'].cohort.ending_date,
                'stage': model['cohort_user'].cohort.stage,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 With profile academy
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test__with_profile_academy(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'},
                                     profile_academy=True)

        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        url = reverse_lazy('admissions:cohort_user')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
            },
            'profile_academy': {
                'id': model['profile_academy'].id,
                'first_name': model['profile_academy'].first_name,
                'last_name': model['profile_academy'].last_name,
                'email': model['profile_academy'].email,
                'phone': model['profile_academy'].phone,
            },
            'cohort': {
                'id': model['cohort_user'].cohort.id,
                'slug': model['cohort_user'].cohort.slug,
                'name': model['cohort_user'].cohort.name,
                'kickoff_date': re.sub(r'\+00:00$', 'Z',
                                       model['cohort_user'].cohort.kickoff_date.isoformat()),
                'ending_date': model['cohort_user'].cohort.ending_date,
                'stage': model['cohort_user'].cohort.stage,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_with_data_with_academy_with_comma(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'})
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?academy=' + model['cohort_user'].cohort.academy.slug + ',they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
            },
            'profile_academy': None,
            'cohort': {
                'id': model['cohort_user'].cohort.id,
                'slug': model['cohort_user'].cohort.slug,
                'name': model['cohort_user'].cohort.name,
                'kickoff_date': re.sub(r'\+00:00$', 'Z',
                                       model['cohort_user'].cohort.kickoff_date.isoformat()),
                'ending_date': model['cohort_user'].cohort.ending_date,
                'stage': model['cohort_user'].cohort.stage,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_with_data_with_bad_cohorts(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
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
    def test_with_data_with_cohorts(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'})
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:cohort_user')
        url = f'{base_url}?cohorts=' + model['cohort_user'].cohort.slug
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['cohort_user'].id,
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
            },
            'profile_academy': None,
            'cohort': {
                'id': model['cohort_user'].cohort.id,
                'slug': model['cohort_user'].cohort.slug,
                'name': model['cohort_user'].cohort.name,
                'kickoff_date': re.sub(r'\+00:00$', 'Z',
                                       model['cohort_user'].cohort.kickoff_date.isoformat()),
                'ending_date': model['cohort_user'].cohort.ending_date,
                'stage': model['cohort_user'].cohort.stage,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_put_without_id(self):
        """Test /cohort/user without auth"""
        url = reverse_lazy('admissions:cohort_user')
        model = self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'status_code': 400, 'detail': 'Missing cohort_id, user_id and id'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_put_in_bulk_without_data(self):
        """Test /cohort/user without auth"""
        url = reverse_lazy('admissions:cohort_user')
        model = self.generate_models(authenticate=True)
        data = []
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_user_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_put_in_bulk_without_data__without_passing_attrs(self):
        """Test /cohort/user without auth"""
        url = reverse_lazy('admissions:cohort_user')
        model = self.generate_models(authenticate=True)
        data = [{}]
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'detail': 'Missing cohort_id, user_id and id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_put_in_bulk_without_data__cannot_determine_the_cohort_user(self):
        """Test /cohort/user without auth"""
        url = reverse_lazy('admissions:cohort_user')
        model = self.generate_models(authenticate=True)
        data = [{'id': 1}]
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'detail': 'Cannot determine CohortUser in index 0', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_put_in_bulk_without_profile_academy(self):
        """Test /cohort/user without auth"""
        url = reverse_lazy('admissions:cohort_user')
        model = self.generate_models(authenticate=True, cohort_user=True)
        data = [{'id': model['cohort_user'].id}]
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'detail': 'Specified cohort not be found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(), [{
            'id': 1,
            'user_id': 1,
            'cohort_id': 1,
            'role': 'STUDENT',
            'finantial_status': None,
            'educational_status': None,
            'watching': False,
        }])

    def test_put_in_bulk_with_stage_delete(self):
        """Test /cohort/user without auth"""
        cohort_kwargs = {'stage': 'DELETED'}
        url = reverse_lazy('admissions:cohort_user')
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     cohort_kwargs=cohort_kwargs)
        data = [{'id': model['cohort_user'].id}]
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'detail': 'cohort-with-stage-deleted', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(), [{
            'id': 1,
            'user_id': 1,
            'cohort_id': 1,
            'role': 'STUDENT',
            'finantial_status': None,
            'educational_status': None,
            'watching': False,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_put_in_bulk_with_one_item(self):
        """Test /cohort/user without auth"""
        url = reverse_lazy('admissions:cohort_user')
        model = self.generate_models(authenticate=True, cohort_user=True, profile_academy=True)
        data = [{'id': model['cohort_user'].id}]
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = [{
            'id': 1,
            'role': 'STUDENT',
            'educational_status': None,
            'finantial_status': None,
            'watching': False,
        }]

        expected = [
            put_serializer(self,
                           model.cohort_user,
                           model.cohort,
                           model.user,
                           model.profile_academy,
                           data={
                               'role': 'STUDENT',
                           })
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_user_dict(), [{
            'id': 1,
            'user_id': 1,
            'cohort_id': 1,
            'role': 'STUDENT',
            'finantial_status': None,
            'educational_status': None,
            'watching': False,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_put_in_bulk_with_two_items(self):
        """Test /cohort/user without auth"""
        url = reverse_lazy('admissions:cohort_user')
        model = [self.generate_models(authenticate=True, cohort_user=True, profile_academy=True)]

        base = model[0].copy()
        del base['user']
        del base['cohort']
        del base['cohort_user']
        del base['profile_academy']

        model = model + [self.generate_models(cohort_user=True, profile_academy=True, models=base)]

        data = [{
            'id': 1,
            'finantial_status': 'LATE',
        }, {
            'user': '2',
            'cohort': '2',
            'educational_status': 'GRADUATED'
        }]
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = [{
            'id': 1,
            'role': 'STUDENT',
            'educational_status': None,
            'finantial_status': 'LATE',
            'watching': False,
        }, {
            'id': 2,
            'role': 'STUDENT',
            'educational_status': 'GRADUATED',
            'finantial_status': None,
            'watching': False,
        }]
        expected = [
            put_serializer(self,
                           m.cohort_user,
                           m.cohort,
                           m.user,
                           m.profile_academy,
                           data={
                               'educational_status': None if m.cohort.id == 1 else 'GRADUATED',
                               'finantial_status': 'LATE' if m.cohort.id == 1 else None,
                           }) for m in model
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_user_dict(), [{
            'id': 1,
            'user_id': 1,
            'cohort_id': 1,
            'role': 'STUDENT',
            'finantial_status': 'LATE',
            'educational_status': None,
            'watching': False,
        }, {
            'id': 2,
            'user_id': 2,
            'cohort_id': 2,
            'role': 'STUDENT',
            'finantial_status': None,
            'educational_status': 'GRADUATED',
            'watching': False,
        }])

    # that's methods name is irrelevant because it's deprecated

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_delete_without_auth(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('admissions:cohort_user')
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.all_cohort_user_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_delete_without_args_in_url_or_bulk(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        url = reverse_lazy('admissions:cohort_user')
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'Missing user_id or cohort_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_delete_in_bulk_with_one(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='crud_cohort',
                                    role='potato')

        del base['user']
        del base['cohort']

        for field in many_fields:
            cohort_user_kwargs = {
                'role': choice(['STUDENT', 'ASSISTANT', 'TEACHER']),
                'finantial_status': choice(['FULLY_PAID', 'UP_TO_DATE', 'LATE']),
                'educational_status': choice(['ACTIVE', 'POSTPONED', 'SUSPENDED', 'GRADUATED', 'DROPPED']),
            }
            model = self.generate_models(cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base)
            url = (reverse_lazy('admissions:cohort_user') + f'?{field}=' +
                   str(getattr(model['cohort_user'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_cohort_user_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_delete_in_bulk_with_two(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields = ['id']

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='crud_cohort',
                                    role='potato')

        del base['user']
        del base['cohort']

        for field in many_fields:
            cohort_user_kwargs = {
                'role': choice(['STUDENT', 'ASSISTANT', 'TEACHER']),
                'finantial_status': choice(['FULLY_PAID', 'UP_TO_DATE', 'LATE']),
                'educational_status': choice(['ACTIVE', 'POSTPONED', 'SUSPENDED', 'GRADUATED', 'DROPPED']),
            }
            model1 = self.generate_models(cohort_user=True,
                                          cohort_user_kwargs=cohort_user_kwargs,
                                          models=base)

            cohort_user_kwargs = {
                'role': choice(['STUDENT', 'ASSISTANT', 'TEACHER']),
                'finantial_status': choice(['FULLY_PAID', 'UP_TO_DATE', 'LATE']),
                'educational_status': choice(['ACTIVE', 'POSTPONED', 'SUSPENDED', 'GRADUATED', 'DROPPED']),
            }
            model2 = self.generate_models(cohort_user=True,
                                          cohort_user_kwargs=cohort_user_kwargs,
                                          models=base)
            url = (reverse_lazy('admissions:cohort_user') + f'?{field}=' +
                   str(getattr(model1['cohort_user'], field)) + ',' +
                   str(getattr(model2['cohort_user'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_cohort_user_dict(), [])

    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    def test_with_data(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)

        url = reverse_lazy('admissions:cohort_user')
        response = self.client.get(url)
        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['CacheExtension', 'PaginationExtension']),
        ])
        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(cache=CohortUserCache, paginate=True),
        ])

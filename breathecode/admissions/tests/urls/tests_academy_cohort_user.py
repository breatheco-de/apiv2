"""
Test /cohort/user
"""
import random
import re
from unittest.mock import MagicMock, patch
from django.utils import timezone
from random import choice
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.admissions.models import STARTED
from ..mixins import AdmissionsTestCase

UTC_NOW = timezone.now()


def cohort_user_item(data={}):
    return {
        'cohort_id': 0,
        'educational_status': None,
        'finantial_status': None,
        'id': 0,
        'role': 'STUDENT',
        'user_id': 0,
        'watching': False,
        'history_log': {},
        **data,
    }


def post_serializer(self, cohort, user, profile_academy=None, data={}):
    return {
        'cohort': {
            'ending_date':
            cohort.ending_date,
            'id':
            cohort.id,
            'kickoff_date':
            self.bc.datetime.to_iso_string(cohort.kickoff_date)
            if cohort.kickoff_date else cohort.kickoff_date,
            'name':
            cohort.name,
            'slug':
            cohort.slug,
            'stage':
            cohort.stage,
            'available_as_saas':
            cohort.available_as_saas,
        },
        'created_at': self.bc.datetime.to_iso_string(UTC_NOW),
        'educational_status': None,
        'finantial_status': None,
        'id': 1,
        'profile_academy': {
            'email': profile_academy.email,
            'first_name': profile_academy.first_name,
            'id': profile_academy.id,
            'last_name': profile_academy.last_name,
            'phone': profile_academy.phone,
        } if profile_academy else None,
        'role': 'STUDENT',
        'user': {
            'email': user.email,
            'first_name': user.first_name,
            'id': user.id,
            'last_name': user.last_name,
        },
        'watching': False,
        **data,
    }


def put_serializer(self, cohort_user, cohort, user, profile_academy=None, data={}):
    return {
        'cohort': {
            'ending_date':
            cohort.ending_date,
            'id':
            cohort.id,
            'kickoff_date':
            self.bc.datetime.to_iso_string(cohort.kickoff_date)
            if cohort.kickoff_date else cohort.kickoff_date,
            'name':
            cohort.name,
            'slug':
            cohort.slug,
            'stage':
            cohort.stage,
            'available_as_saas':
            cohort.available_as_saas,
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
    """
    🔽🔽🔽 Auth
    """

    def test__without_auth(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_user')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 Without data
    """

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__without_data(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        url = reverse_lazy('admissions:academy_cohort_user')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 0)

    """
    🔽🔽🔽 With data
    """

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        url = reverse_lazy('admissions:academy_cohort_user')
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
                'available_as_saas': model['cohort_user'].cohort.available_as_saas,
            },
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
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 Roles in querystring
    """

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_bad_roles(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort_user')
        url = f'{base_url}?roles=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    def test__with_data__with_roles(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        role = model['cohort_user'].role

        if random.randint(0, 1):
            role = role.lower()

        url = reverse_lazy('admissions:academy_cohort_user') + f'?roles={role}'
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
                'available_as_saas': model['cohort_user'].cohort.available_as_saas,
            },
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
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_roles__with_comma(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort_user')
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
                'available_as_saas': model['cohort_user'].cohort.available_as_saas,
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

    """
    🔽🔽🔽 Finantial status in querystring
    """

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_bad_finantial_status(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort_user')
        url = f'{base_url}?finantial_status=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_finantial_status(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'finantial_status': 'LATE'},
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        role = model['cohort_user'].finantial_status

        if random.randint(0, 1):
            role = role.lower()

        url = reverse_lazy('admissions:academy_cohort_user') + f'?finantial_status={role}'
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
                'available_as_saas': model['cohort_user'].cohort.available_as_saas,
            },
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
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_finantial_status__with_comma(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'finantial_status': 'LATE'},
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort_user')
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
                'available_as_saas': model['cohort_user'].cohort.available_as_saas,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 Educational status in querystring
    """

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_bad_educational_status(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort_user')
        url = f'{base_url}?educational_status=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_educational_status(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'},
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        role = model['cohort_user'].educational_status

        if random.randint(0, 1):
            role = role.lower()

        url = reverse_lazy('admissions:academy_cohort_user') + f'?educational_status={role}'
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
                'available_as_saas': model['cohort_user'].cohort.available_as_saas,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_educational_status__with_comma(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'},
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort_user')
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
                'available_as_saas': model['cohort_user'].cohort.available_as_saas,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 Academy in querystring
    """

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_academy(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'},
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort_user')
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
                'available_as_saas': model['cohort_user'].cohort.available_as_saas,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_academy__with_comma(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'},
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort_user')
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
                'available_as_saas': model['cohort_user'].cohort.available_as_saas,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 Cohorts in querystring
    """

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_bad_cohorts(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort_user')
        url = f'{base_url}?cohorts=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__with_data__with_cohorts(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'},
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort_user')
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
                'available_as_saas': model['cohort_user'].cohort.available_as_saas,
            },
            'watching': False,
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 Put without id
    """

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__put__without_id(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_user')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        data = {}
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'status_code': 400, 'detail': 'Missing cohort_id, user_id and id'}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    """
    🔽🔽🔽 Put bulk mode
    """

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__put__in_bulk__without_data(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_user')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        data = []
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__put__in_bulk__without_data__without_id(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_user')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        data = [{}]
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'detail': 'Missing cohort_id, user_id and id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__put__in_bulk__without_data__with_bad_id(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_user')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        data = [{'id': 1}]
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'detail': 'Cannot determine CohortUser in index 0', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__put__in_bulk__with_one_item(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_user')
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        data = [{'id': model['cohort_user'].id}]
        response = self.client.put(url, data, format='json')
        json = response.json()
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
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            self.bc.format.to_dict(model.cohort_user),
        ])

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__put__in_bulk__with_two_items(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_user')
        model = [
            self.generate_models(authenticate=True,
                                 cohort_user=True,
                                 profile_academy=True,
                                 capability='crud_cohort',
                                 role='potato')
        ]

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
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            {
                **self.bc.format.to_dict(model[0].cohort_user),
                'finantial_status': 'LATE',
            },
            {
                **self.bc.format.to_dict(model[1].cohort_user),
                'educational_status': 'GRADUATED',
            },
        ])

    """
    🔽🔽🔽 Post bulk mode
    """

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__post__in_bulk__0_items(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        url = reverse_lazy('admissions:academy_cohort_user')
        data = []
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__post__in_bulk__1_item(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort={'stage': 'STARTED'},
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        url = reverse_lazy('admissions:academy_cohort_user')
        data = [{
            'user': model['user'].id,
            'cohort': model['cohort'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = [
            post_serializer(self,
                            model.cohort,
                            model.user,
                            model.profile_academy,
                            data={
                                'id': 1,
                                'role': 'STUDENT',
                            }),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            cohort_user_item({
                'cohort_id': 1,
                'id': 1,
                'user_id': 1,
            }),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__post_in_bulk__2_items(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    cohort={'stage': 'STARTED'},
                                    profile_academy=True,
                                    capability='crud_cohort',
                                    role='potato')
        del base['user']

        models = [self.generate_models(user=True, models=base) for _ in range(0, 2)]
        url = reverse_lazy('admissions:academy_cohort_user')
        data = [{
            'user': model['user'].id,
            'cohort': models[0]['cohort'].id,
        } for model in models]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = [
            post_serializer(self,
                            model.cohort,
                            model.user,
                            None,
                            data={
                                'id': model.user.id - 1,
                                'role': 'STUDENT',
                            }) for model in models
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            cohort_user_item({
                'cohort_id': 1,
                'id': 1,
                'user_id': 2,
            }),
            cohort_user_item({
                'cohort_id': 1,
                'id': 2,
                'user_id': 3,
            }),
        ])

    """
    🔽🔽🔽 Post in bulk, statuses in lowercase
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__post__in_bulk__1_item__statuses_in_lowercase(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)

        model = self.generate_models(authenticate=True,
                                     cohort={'stage': 'STARTED'},
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        url = reverse_lazy('admissions:academy_cohort_user')
        role = random.choice(['TEACHER', 'ASSISTANT', 'REVIEWER', 'STUDENT']).lower()
        finantial_status = random.choice(['FULLY_PAID', 'UP_TO_DATE', 'LATE']).lower()
        # don't put GRADUATED here
        educational_status = random.choice(['ACTIVE', 'POSTPONED', 'SUSPENDED', 'DROPPED']).lower()
        data = [{
            'role': role,
            'finantial_status': finantial_status,
            'educational_status': educational_status,
            'user': model['user'].id,
            'cohort': model['cohort'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()

        del data[0]['user']
        del data[0]['cohort']

        expected = [
            post_serializer(self,
                            model.cohort,
                            model.user,
                            model.profile_academy,
                            data={
                                **data[0],
                                'role': role.upper(),
                                'finantial_status': finantial_status.upper(),
                                'educational_status': educational_status.upper(),
                            }),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            cohort_user_item({
                'cohort_id': 1,
                'role': role.upper(),
                'finantial_status': finantial_status.upper(),
                'educational_status': educational_status.upper(),
                'id': 1,
                'user_id': 1,
            }),
        ])

    """
    🔽🔽🔽 Delete in bulk
    """

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__delete__without_args_in_url_or_bulk(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        url = reverse_lazy('admissions:academy_cohort_user')
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'Missing user_id or cohort_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__delete__in_bulk__with_one(self):
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
            url = (reverse_lazy('admissions:academy_cohort_user') + f'?{field}=' +
                   str(getattr(model['cohort_user'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test__delete__in_bulk__with_two(self):
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
            url = (reverse_lazy('admissions:academy_cohort_user') + f'?{field}=' +
                   str(getattr(model1['cohort_user'], field)) + ',' +
                   str(getattr(model2['cohort_user'], field)))
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test_academy_cohort_user__post__1_item(self):

        prohibited_stages = ['INACTIVE', 'DELETED', 'ENDED']
        for stage in prohibited_stages:

            model = self.generate_models(authenticate=True,
                                         cohort={'stage': stage},
                                         user=True,
                                         profile_academy=True,
                                         capability='crud_cohort',
                                         role='potato')

            self.headers(academy=model.academy.id)

            url = reverse_lazy('admissions:academy_cohort_user')
            data = {
                'user': model['user'].id,
                'cohort': model['cohort'].id,
            }

            response = self.client.post(url, data, format='json')
            json = response.json()
            expected = {'detail': 'adding-student-to-a-closed-cohort', 'status_code': 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    def test_academy_cohort_user__post__2_item(self):
        #incomplete test
        prohibited_stages = ['INACTIVE', 'DELETED', 'ENDED']
        for stage in prohibited_stages:

            model = self.generate_models(authenticate=True,
                                         cohort=(2, {
                                             'stage': stage
                                         }),
                                         user=True,
                                         profile_academy=True,
                                         capability='crud_cohort',
                                         role='potato')

            self.headers(academy=model.academy.id)

            url = reverse_lazy('admissions:academy_cohort_user')
            data = [{
                'user': model['user'].id,
                'cohort': model['cohort'][0].id,
            }, {
                'user': model['user'].id,
                'cohort': model['cohort'][1].id,
            }]
            response = self.client.post(url, data, format='json')
            json = response.json()
            expected = {'detail': 'adding-student-to-a-closed-cohort', 'status_code': 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

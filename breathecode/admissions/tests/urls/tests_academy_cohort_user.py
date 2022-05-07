"""
Test /cohort/user
"""
import re
from random import choice
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""
    """
    🔽🔽🔽 Auth
    """
    def test_academy_cohort_user__without_auth(self):
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

    def test_academy_cohort_user__without_data(self):
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

    def test_academy_cohort_user__with_data(self):
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 Roles in querystring
    """

    def test_academy_cohort_user__with_data__with_bad_roles(self):
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

    def test_academy_cohort_user__with_data__with_roles(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:academy_cohort_user')
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
            'profile_academy': {
                'id': model['profile_academy'].id,
                'first_name': model['profile_academy'].first_name,
                'last_name': model['profile_academy'].last_name,
                'email': model['profile_academy'].email,
                'phone': model['profile_academy'].phone,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    def test_academy_cohort_user__with_data__with_roles__with_comma(self):
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
            },
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 Finantial status in querystring
    """

    def test_academy_cohort_user__with_data__with_bad_finantial_status(self):
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

    def test_academy_cohort_user__with_data__with_finantial_status(self):
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
            'profile_academy': {
                'id': model['profile_academy'].id,
                'first_name': model['profile_academy'].first_name,
                'last_name': model['profile_academy'].last_name,
                'email': model['profile_academy'].email,
                'phone': model['profile_academy'].phone,
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    def test_academy_cohort_user__with_data__with_finantial_status__with_comma(self):
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
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 Educational status in querystring
    """

    def test_academy_cohort_user__with_data__with_bad_educational_status(self):
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

    def test_academy_cohort_user__with_data__with_educational_status(self):
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
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    def test_academy_cohort_user__with_data__with_educational_status__with_comma(self):
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
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 Academy in querystring
    """

    def test_academy_cohort_user__with_data__with_academy(self):
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
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    def test_academy_cohort_user__with_data__with_academy__with_comma(self):
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
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 Cohorts in querystring
    """

    def test_academy_cohort_user__with_data__with_bad_cohorts(self):
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

    def test_academy_cohort_user__with_data__with_cohorts(self):
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
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 Put without id
    """

    def test_academy_cohort_user__put__without_id(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_user')
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {'status_code': 400, 'detail': 'Missing cohort_id or user_id'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(), [])

    """
    🔽🔽🔽 Put bulk mode
    """

    def test_academy_cohort_user__put__in_bulk__without_data(self):
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
        self.assertEqual(self.all_cohort_user_dict(), [])

    def test_academy_cohort_user__put__in_bulk__without_data(self):
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
        expected = {'detail': 'Cannot determine CohortUser in index 0', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(), [])

    def test_academy_cohort_user__put__in_bulk__with_one_item(self):
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
        expected = [{'id': 1, 'role': 'STUDENT', 'educational_status': None, 'finantial_status': None}]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_user_dict(), [{
            'id': 1,
            'user_id': 1,
            'cohort_id': 1,
            'role': 'STUDENT',
            'finantial_status': None,
            'educational_status': None
        }])

    def test_academy_cohort_user__put__in_bulk__with_two_items(self):
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
        expected = [{
            'id': 1,
            'role': 'STUDENT',
            'educational_status': None,
            'finantial_status': 'LATE',
        }, {
            'id': 2,
            'role': 'STUDENT',
            'educational_status': 'GRADUATED',
            'finantial_status': None
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_user_dict(), [{
            'id': 1,
            'user_id': 1,
            'cohort_id': 1,
            'role': 'STUDENT',
            'finantial_status': 'LATE',
            'educational_status': None
        }, {
            'id': 2,
            'user_id': 2,
            'cohort_id': 2,
            'role': 'STUDENT',
            'finantial_status': None,
            'educational_status': 'GRADUATED'
        }])

    """
    🔽🔽🔽 Post bulk mode
    """

    def test_academy_cohort_user__post__in_bulk__0_items(self):
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
        self.assertEqual(self.all_cohort_user_dict(), [])

    def test_academy_cohort_user__post__in_bulk__1_item(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
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
        expected = [{
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
                'remote_available': True,
                'kickoff_date': re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
                'current_day': model['cohort'].current_day,
                'online_meeting_url': model['cohort'].online_meeting_url,
                'timezone': model['cohort'].timezone,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'schedule': None,
                'syllabus_version': None,
                'ending_date': model['cohort'].ending_date,
                'stage': model['cohort'].stage,
                'language': model['cohort'].language,
                'created_at': re.sub(r'\+00:00$', 'Z', model['cohort'].created_at.isoformat()),
                'updated_at': re.sub(r'\+00:00$', 'Z', model['cohort'].updated_at.isoformat()),
            },
        }]

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

    def test_academy_cohort_user__post_in_bulk__2_items(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    cohort=True,
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
        expected = [{
            'id': model['user'].id - 1,
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
                'remote_available': True,
                'kickoff_date': re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
                'current_day': model['cohort'].current_day,
                'online_meeting_url': model['cohort'].online_meeting_url,
                'timezone': model['cohort'].timezone,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'schedule': None,
                'syllabus_version': None,
                'ending_date': model['cohort'].ending_date,
                'stage': model['cohort'].stage,
                'language': model['cohort'].language,
                'created_at': re.sub(r'\+00:00$', 'Z', model['cohort'].created_at.isoformat()),
                'updated_at': re.sub(r'\+00:00$', 'Z', model['cohort'].updated_at.isoformat()),
            },
        } for model in models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'STUDENT',
            'user_id': 2,
        }, {
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 2,
            'role': 'STUDENT',
            'user_id': 3,
        }])

    """
    🔽🔽🔽 Delete in bulk
    """

    def test_academy_cohort_user__delete__without_args_in_url_or_bulk(self):
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
        self.assertEqual(self.all_cohort_user_dict(), [])

    def test_academy_cohort_user__delete__in_bulk__with_one(self):
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
            self.assertEqual(self.all_cohort_user_dict(), [])

    def test_academy_cohort_user__delete__in_bulk__with_two(self):
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
            self.assertEqual(self.all_cohort_user_dict(), [])

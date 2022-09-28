"""
Test /cohort/all
"""
from datetime import timedelta
import random
import re
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status
from ..mixins import AdmissionsTestCase


def get_serializer(cohort_user, user):
    return {
        'role': cohort_user.role,
        'user': {
            'first_name': user.first_name,
            'last_name': user.last_name,
        },
    }


class CohortAllTestSuite(AdmissionsTestCase):
    """Test /cohort/all"""

    def test_without_auth(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:public_cohort_user')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 0)

    def test_without_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:public_cohort_user')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 0)

    """
    🔽🔽🔽 With data
    """

    def test_with_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        url = reverse_lazy('admissions:public_cohort_user')
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort_user, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [{
            **self.model_to_dict(model, 'cohort_user')
        }])

    """
    🔽🔽🔽 roles in querystring
    """

    def test_with_data_with_bad_roles(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:public_cohort_user')
        url = f'{base_url}?roles=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    def test_with_data_with_roles(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        role = model['cohort_user'].role

        if random.randint(0, 1):
            role = role.lower()

        url = reverse_lazy('admissions:public_cohort_user') + f'?roles=' + role
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort_user, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    def test_with_data_with_roles_with_comma(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:public_cohort_user')
        url = f'{base_url}?roles=' + model['cohort_user'].role + ',they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        expected = [get_serializer(model.cohort_user, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 finantial_status in querystring
    """

    def test_with_data_with_bad_finantial_status(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:public_cohort_user')
        url = f'{base_url}?finantial_status=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    def test_with_data_with_finantial_status(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'finantial_status': 'LATE'})
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        role = model['cohort_user'].finantial_status

        if random.randint(0, 1):
            role = role.lower()

        url = reverse_lazy('admissions:public_cohort_user') + f'?finantial_status=' + role
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort_user, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    def test_with_data_with_finantial_status_with_comma(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'finantial_status': 'LATE'})
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:public_cohort_user')
        url = (f'{base_url}?finantial_status=' + model['cohort_user'].finantial_status + ',they-killed-kenny')
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort_user, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    """
    🔽🔽🔽 educational_status in querystring
    """

    def test_with_data_with_bad_educational_status(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True, cohort_user=True)
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:public_cohort_user')
        url = f'{base_url}?educational_status=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    def test_with_data_with_educational_status(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'})
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:public_cohort_user')
        role = model['cohort_user'].educational_status

        if random.randint(0, 1):
            role = role.lower()

        url = reverse_lazy('admissions:public_cohort_user') + f'?educational_status=' + role
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort_user, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

    def test_with_data_with_educational_status_with_comma(self):
        """Test /cohort/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     cohort_user_kwargs={'educational_status': 'GRADUATED'})
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        base_url = reverse_lazy('admissions:public_cohort_user')
        url = (f'{base_url}?educational_status=' + model['cohort_user'].educational_status + ','
               'they-killed-kenny')
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort_user, model.user)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.get_cohort_user_dict(1), model_dict)

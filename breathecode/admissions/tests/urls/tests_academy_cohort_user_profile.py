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
                                     capability='read_cohort',
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
                                     profile=True,
                                     capability='read_cohort',
                                     role='potato')
        model_dict = self.remove_dinamics_fields(model['cohort_user'].__dict__)
        url = reverse_lazy('admissions:academy_cohort_user')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'role': model['cohort_user'].role,
            'finantial_status': model['cohort_user'].finantial_status,
            'educational_status': model['cohort_user'].educational_status,
            'created_at': re.sub(r'\+00:00$', 'Z', model['cohort_user'].created_at.isoformat()),
            'id': model['cohort_user'].id,
            'user': {
                'id': model['cohort_user'].user.id,
                'first_name': model['cohort_user'].user.first_name,
                'last_name': model['cohort_user'].user.last_name,
                'email': model['cohort_user'].user.email,
                'profile': {
                    'id': model['cohort_user'].user.profile.id,
                    'avatar_url': model['cohort_user'].user.profile.avatar_url,
                    'github_username': model['cohort_user'].user.profile.github_username,
                    'show_tutorial': model['cohort_user'].user.profile.show_tutorial,
                },
            },
            'profile': {
                'id': model['cohort_user'].user.profile.id,
                'avatar_url': model['cohort_user'].user.profile.avatar_url,
                'github_username': model['cohort_user'].user.profile.github_username,
                'show_tutorial': model['cohort_user'].user.profile.show_tutorial,
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

"""
Test cases for /user
"""
import pytz, datetime
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    """
    🔽🔽🔽 Auth
    """
    def test_user_me__without_auth(self):
        """Test /user/me without auth"""
        url = reverse_lazy('authenticate:user_me')
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 Get
    """

    def test_user_me(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True)

        url = reverse_lazy('authenticate:user_me')
        response = self.client.get(url)

        json = response.json()
        expected = {
            'id': model.user.id,
            'email': model.user.email,
            'first_name': model.user.first_name,
            'last_name': model.user.last_name,
            'github': None,
            'roles': [],
        }

        self.assertEqual(json, expected)

    """
    🔽🔽🔽 Get with CredentialsGithub
    """

    def test_user_me__with_github_credentials(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True, credentials_github=True)

        url = reverse_lazy('authenticate:user_me')
        response = self.client.get(url)

        json = response.json()
        expected = {
            'id': model.user.id,
            'email': model.user.email,
            'first_name': model.user.first_name,
            'last_name': model.user.last_name,
            'github': {
                'avatar_url': None,
                'name': None,
                'username': None,
            },
            'roles': [],
        }

        self.assertEqual(json, expected)

    """
    🔽🔽🔽 Get with ProfileAcademy
    """

    def test_user_me__with_profile_academy(self):
        """Test /user/me"""
        model = self.generate_models(authenticate=True, profile_academy=True)

        url = reverse_lazy('authenticate:user_me')
        response = self.client.get(url)

        json = response.json()
        expected = {
            'id':
            model.user.id,
            'email':
            model.user.email,
            'first_name':
            model.user.first_name,
            'last_name':
            model.user.last_name,
            'github':
            None,
            'roles': [
                {
                    'academy': {
                        'id': model.academy.id,
                        'name': model.academy.name,
                        'slug': model.academy.slug,
                        'timezone': model.academy.timezone,
                    },
                    'created_at': pytz.utc.localize(model.profile_academy.created_at),
                    'id': model.profile_academy.id,
                    'role': model.profile_academy.role.slug,
                },
            ],
        }

        self.assertEqual(json, expected)

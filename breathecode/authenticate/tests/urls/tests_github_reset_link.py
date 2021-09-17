from breathecode.authenticate.models import ProfileAcademy, Token
import re
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase
from breathecode.services import datetime_to_iso_format


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_github_reset_link_without_auth(self):
        """Test /auth/member/<profile_academy_id>/token"""
        url = reverse_lazy('authenticate:reset_github_link', kwargs={'profile_academy_id': 3})
        response = self.client.post(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED,
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_github_reset_link_without_capability(self):
        """Test /auth/member/<profile_academy_id>/token"""
        self.headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:reset_github_link', kwargs={'profile_academy_id': 3})
        response = self.client.post(url)
        json = response.json()

        self.assertEqual(
            json, {
                'detail': "You (user: 1) don't have this capability: generate_token "
                'for academy 1',
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_github_reset_link_without_user(self):
        """Test /auth/member/<profile_academy_id>/token"""
        role = 'pikachu'
        self.headers(academy=1)
        self.generate_models(authenticate=True, capability='generate_token', profile_academy=True, role=role)
        url = reverse_lazy('authenticate:reset_github_link', kwargs={'profile_academy_id': 3})
        response = self.client.post(url)
        json = response.json()

        self.assertEqual(json, {'detail': 'Member not found', 'status_code': 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_github_reset_link_ok(self):
        """Test /auth/member/<profile_academy_id>/token"""
        role = 'academy_token'
        self.headers(academy=1)
        profile_academy_kwargs = {'id': 3}
        self.generate_models(authenticate=True,
                             user=True,
                             capability='generate_token',
                             profile_academy=True,
                             role=role,
                             profile_academy_kwargs=profile_academy_kwargs)
        url = reverse_lazy('authenticate:reset_github_link', kwargs={'profile_academy_id': 3})
        response = self.client.post(url)
        json = response.json()

        profile_academy = ProfileAcademy.objects.filter(id=profile_academy_kwargs['id']).first()

        token, created = Token.get_or_create(user=profile_academy.user, token_type='temporal')

        self.assertEqual(
            json, {
                'reset_github_url':
                f'http://localhost:8000/v1/auth/github/{token}?url=https://learn.breatheco.de/login'
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

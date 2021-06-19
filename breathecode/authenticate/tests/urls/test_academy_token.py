from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_academy_token_without_auth(self):
        """Test /academy/:id/member/:id without auth"""
        url = reverse_lazy('authenticate:academy_token')
        response = self.client.post(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED,
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_token_without_capability(self):
        """Test /academy/:id/member/:id without auth"""
        self.headers(academy=1)
        self.generate_models(authenticate=True)
        url = reverse_lazy('authenticate:academy_token')
        response = self.client.post(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: generate_academy_token "
                "for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_token(self):
        """Test /academy/:id/member/:id without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, user=True,
            capability='generate_academy_token', profile_academy=True)
        url = reverse_lazy('authenticate:academy_token')
        response = self.client.post(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: generate_academy_token "
                "for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
import re
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase
from breathecode.services import datetime_to_iso_format
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
        role = 'academy_token'
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, role=role,
            capability='generate_academy_token', profile_academy=True)
        url = reverse_lazy('authenticate:academy_token')
        response = self.client.post(url)
        json = response.json()
        token_pattern = re.compile(r"[0-9a-zA-Z]{,40}$")
        token = self.get_token(1)
        self.assertEqual(bool(token_pattern.match(json['token'])), True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_token_dict(), [{
            'created' : token.created,
            'expires_at': json['expires_at'],
            'id': 1,
            'key': json['token'],
            'token_type' : json['token_type'],
            'user_id' : 2
        }])


    def test_academy_token_refresh_token(self):
        """Test /academy/:id/member/:id without auth"""
        role = 'academy_token'
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, role=role, user=True,
            capability='generate_academy_token', profile_academy=True, token=True)
        url = reverse_lazy('authenticate:academy_token')
        response = self.client.post(url)
        json = response.json()
        token_pattern = re.compile(r"[0-9a-zA-Z]{,40}$")

        self.assertEqual(bool(token_pattern.match(json['token'])), True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_token_dict(), [{
            'created' : model['token'].key,
            'expires_at': json['expires_at'],
            'id': 1,
            'key': json['token'],
            'token_type' : json['token_type'],
            'user_id' : 2
        }])

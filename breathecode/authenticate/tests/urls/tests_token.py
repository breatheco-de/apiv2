"""
Test cases for /user
"""
import re
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_token_without_auth(self):
        """Test /logout without auth"""
        url = reverse_lazy('authenticate:token')
        data = {'email': self.email, 'password': self.password}
        # return client.post(url, data)
        response = self.client.post(url, data)

        detail = str(response.data['detail'])
        status_code = int(response.data['status_code'])

        self.assertEqual(len(response.data), 2)
        self.assertEqual(detail,
                         'Authentication credentials were not provided.')
        self.assertEqual(status_code, 401)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token(self):
        """Test /token"""
        login_response = self.login()
        token = str(login_response.data['token'])
        token_pattern = re.compile("^[0-9a-zA-Z]{,40}$")

        url = reverse_lazy('authenticate:token')
        data = {'email': self.email, 'password': self.password}
        response = self.client.post(url, data)

        token = str(response.data['token'])
        token_type = str(response.data['token_type'])
        expires_at = response.data['expires_at']  # test it
        user_id = int(response.data['user_id'])
        email = response.data['email']

        # self.assertEqual(len(response.data), 2)
        self.assertEqual(len(token), 40)
        self.assertEqual(bool(token_pattern.match(token)), True)
        self.assertEqual(token_type, 'temporal')
        # self.assertEqual(expires_at, 'temporal')
        self.assertEqual(user_id, 1)
        self.assertEqual(email, self.email)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_without_auth(self):
        """Test /token without auth"""
        url = reverse_lazy('authenticate:user')
        data = {'email': self.email, 'password': self.password}
        # return client.post(url, data)
        response = self.client.post(url, data)

        detail = str(response.data['detail'])
        status_code = int(response.data['status_code'])

        self.assertEqual(len(response.data), 2)
        self.assertEqual(detail,
                         'Authentication credentials were not provided.')
        self.assertEqual(status_code, 401)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

"""
Test cases for /user
"""
from django.urls.base import reverse_lazy
from rest_framework import status
from .mixin import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_user_me_without_auth(self):
        """Test /user/me without auth"""
        url = reverse_lazy('authenticate:user_me')
        data = { 'email': self.email, 'password': self.password }
        # return client.post(url, data)
        # self.client.force_authenticate(user=self.user)
        response = self.client.post(url, data)
        detail = str(response.data['detail'])
        status_code = int(response.data['status_code'])

        self.assertEqual(len(response.data), 2)
        self.assertEqual(detail, 'Authentication credentials were not provided.')
        self.assertEqual(status_code, 401)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_me(self):
        """Test /user/me"""
        # self.login()
        url = reverse_lazy('authenticate:user_me')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        user = response.data
        id = user['id']
        email = user['email']
        first_name = user['first_name']
        last_name = user['last_name']
        github = user['github']

        self.assertEqual(5, len(user))
        self.assertEqual(id, self.user.id)
        self.assertEqual(email, self.user.email)
        self.assertEqual(first_name, self.user.first_name)
        self.assertEqual(last_name, self.user.last_name)
        self.assertEqual(github, {'avatar_url': None, 'name': None})

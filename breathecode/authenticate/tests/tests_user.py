"""
Test cases for /user
"""
from django.urls.base import reverse_lazy
from rest_framework import status
from .mixin import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_user_without_auth(self):
        """Test /user without auth"""
        url = reverse_lazy('authenticate:user')
        data = { 'email': self.email, 'password': self.password }
        # return client.post(url, data)
        response = self.client.post(url, data)
        detail = str(response.data['detail'])
        status_code = int(response.data['status_code'])

        self.assertEqual(len(response.data), 2)
        self.assertEqual(detail, 'Authentication credentials were not provided.')
        self.assertEqual(status_code, 401)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user(self):
        """Test /user"""
        # self.login()
        url = reverse_lazy('authenticate:user')

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)

        users = response.data
        id = users[0]['id']
        email = users[0]['email']
        first_name = users[0]['first_name']
        last_name = users[0]['last_name']

        self.assertEqual(1, len(users))
        self.assertEqual(4, len(users[0]))
        self.assertEqual(id, self.user.id)
        self.assertEqual(email, self.user.email)
        self.assertEqual(first_name, self.user.first_name)
        self.assertEqual(last_name, self.user.last_name)

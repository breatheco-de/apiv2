"""
Test cases for /user
"""

import re
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""

    def test_logout_without_token(self):
        """Test /logout without token"""
        self.create_user()

        url = reverse_lazy("authenticate:logout")
        response = self.client.get(url)

        detail = str(response.data["detail"])
        status_code = int(response.data["status_code"])

        self.assertEqual(len(response.data), 2)
        self.assertEqual(detail, "Authentication credentials were not provided.")
        self.assertEqual(status_code, 401)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # def test_logout(self):
    #     """Test /logout"""
    #     url = reverse_lazy('authenticate:logout')

    #     self.client.force_authenticate(user=self.user)

    #     response = self.client.get(url)
    #     message = str(response.data['message'])

    #     self.assertEqual(len(response.data), 1)
    #     self.assertEqual(message, 'User tokens successfully deleted')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

"""
Test cases for /user
"""
import re
from rest_framework import status
from .mixin import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    def test_login_with_bad_credentials(self):
        """Test /login with incorrect credentials"""
        response = self.create_user(email='Konan@naruto.io', password='Pain!$%')

        non_field_errors = response.data['non_field_errors']
        status_code = response.data['status_code']

        self.assertEqual(len(response.data), 2)
        self.assertEqual(non_field_errors, ['Unable to log in with provided credentials.'])
        self.assertEqual(status_code, 400)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_login(self):
        """Test /login"""
        response = self.create_user()
        token_pattern = re.compile("^[0-9a-zA-Z]{,40}$")

        token = str(response.data['token'])
        user_id = int(response.data['user_id'])
        email = str(response.data['email'])

        self.assertEqual(len(response.data), 3)
        self.assertEqual(len(token), 40)
        self.assertEqual(bool(token_pattern.match(token)), True)
        self.assertEqual(user_id, 1)
        self.assertEqual(email, self.email)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

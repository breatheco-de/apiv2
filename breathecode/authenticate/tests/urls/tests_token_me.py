"""
Test cases for /user
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.tests.mixins.breathecode_mixin.breathecode import fake

from ..mixins.new_auth_test_case import AuthTestCase

UTC_NOW = timezone.now()
TOKEN = fake.name()


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""

    def test__auth__without_auth(self):
        """Test /logout without auth"""
        url = reverse_lazy("authenticate:token_me")

        self.bc.database.create(user=1)
        response = self.client.post(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of("authenticate.Token"), [])

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch(
        "rest_framework.authtoken.models.Token.generate_key",
        MagicMock(
            side_effect=[
                TOKEN + "1",
                TOKEN + "2",
                TOKEN + "3",
            ]
        ),
    )
    def test__generate_tokens(self):
        """Test /token"""
        cases = [
            (None, "temporal", UTC_NOW + timedelta(minutes=10), 1),
            ({"token_type": "temporal"}, "temporal", UTC_NOW + timedelta(minutes=10), 2),
            ({"token_type": "one_time"}, "one_time", None, 3),
        ]
        for data, token_type, expires_at, index in cases:
            url = reverse_lazy("authenticate:token_me")

            model = self.bc.database.create(user=1)
            self.client.force_authenticate(model.user)
            response = self.client.post(url, data)
            json = response.json()
            expected = {
                "email": model.user.email,
                "expires_at": self.bc.datetime.to_iso_string(expires_at) if expires_at else None,
                "token": TOKEN + str(index),
                "token_type": token_type,
                "user_id": index,
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.bc.database.list_of("authenticate.Token"),
                [
                    {
                        "created": UTC_NOW,
                        "expires_at": expires_at,
                        "id": index,
                        "key": TOKEN + str(index),
                        "token_type": token_type,
                        "user_id": index,
                    }
                ],
            )

            # teardown
            self.bc.database.delete("authenticate.Token")

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch(
        "rest_framework.authtoken.models.Token.generate_key",
        MagicMock(
            side_effect=[
                TOKEN + "1",
                TOKEN + "2",
                TOKEN + "3",
            ]
        ),
    )
    def test__generate_tokens__bad_token_type(self):
        """Test /token"""
        cases = [
            {"token_type": "login"},
            {"token_type": "permanent"},
        ]
        for data in cases:
            url = reverse_lazy("authenticate:token_me")

            model = self.bc.database.create(user=1)
            self.client.force_authenticate(model.user)
            response = self.client.post(url, data)
            json = response.json()
            expected = {"detail": "token-type-invalid-or-not-allowed", "status_code": 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.bc.database.list_of("authenticate.Token"), [])

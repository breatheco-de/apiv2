"""
Test cases for /user
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth.hashers import make_password
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.activity import tasks as activity_tasks

from ...mixins.new_auth_test_case import AuthTestCase


def user_invite_serializer(self, user_invite, academy=None, cohort=None):
    return {
        "academy": academy,
        "asset_slug": user_invite.asset_slug,
        "clicked_at": user_invite.clicked_at,
        "cohort": cohort,
        "conversion_info": user_invite.conversion_info,
        "course": None,
        "created_at": self.bc.datetime.to_iso_string(user_invite.created_at),
        "email": user_invite.email,
        "event_slug": user_invite.event_slug,
        "first_name": user_invite.first_name,
        "id": user_invite.id,
        "last_name": user_invite.last_name,
        "opened_at": user_invite.opened_at,
        "phone": user_invite.phone,
        "role": user_invite.role,
        "sent_at": user_invite.sent_at,
        "status": user_invite.status,
        "token": user_invite.token,
        "welcome_video": user_invite.welcome_video,
    }


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""

    @patch("breathecode.activity.tasks.add_activity.delay", MagicMock())
    def test_login_with_bad_credentials(self):
        """Test /login with incorrect credentials"""

        url = reverse_lazy("authenticate:login")
        data = {"email": "Konan@naruto.io", "password": "Pain!$%"}
        response = self.client.post(url, data)

        json = response.json()
        expected = {
            "non_field_errors": ["Unable to log in with provided credentials."],
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch("breathecode.activity.tasks.add_activity.delay", MagicMock())
    def test_login_without_email(self):
        """Test /login with incorrect credentials"""

        url = reverse_lazy("authenticate:login")
        data = {"password": "Pain!$%"}
        response = self.client.post(url, data)

        json = response.json()
        expected = {
            "email": ["This field is required."],
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch("breathecode.activity.tasks.add_activity.delay", MagicMock())
    def test_login_without_password(self):
        """Test /login with incorrect credentials"""

        url = reverse_lazy("authenticate:login")
        data = {"email": "Konan@naruto.io"}
        response = self.client.post(url, data)

        json = response.json()
        expected = {
            "password": ["This field is required."],
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch("breathecode.activity.tasks.add_activity.delay", MagicMock())
    def test_login_email_not_verified__no_invites(self):
        """Test /login"""

        password = "Pain!$%"
        user = {"email": "Konan@naruto.io", "password": make_password(password)}
        model = self.bc.database.create(user=user)

        url = reverse_lazy("authenticate:login")
        data = {"email": model.user.email.lower(), "password": password}
        response = self.client.post(url, data)

        json = response.json()
        expected = {
            "detail": "email-not-validated",
            "status_code": 403,
            "silent": True,
            "silent_code": "email-not-validated",
            "data": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch("breathecode.activity.tasks.add_activity.delay", MagicMock())
    def test_login_email_not_verified__with_invites(self):
        """Test /login"""

        password = "Pain!$%"
        user = {"email": "Konan@naruto.io", "password": make_password(password)}
        user_invite = {"email": "Konan@naruto.io", "status": "ACCEPTED", "is_email_validated": False}
        model = self.bc.database.create(user=user, user_invite=(2, user_invite))

        url = reverse_lazy("authenticate:login")
        data = {"email": model.user.email.lower(), "password": password}
        response = self.client.post(url, data)

        json = response.json()
        expected = {
            "detail": "email-not-validated",
            "status_code": 403,
            "silent": True,
            "silent_code": "email-not-validated",
            "data": [
                user_invite_serializer(self, model.user_invite[1]),
                user_invite_serializer(self, model.user_invite[0]),
            ],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch("breathecode.activity.tasks.add_activity.delay", MagicMock())
    def test_login_lowercase_email(self):
        """Test /login"""

        password = "Pain!$%"
        user = {"email": "Konan@naruto.io", "password": make_password(password)}
        user_invite = {"email": "Konan@naruto.io", "status": "ACCEPTED", "is_email_validated": True}
        model = self.bc.database.create(user=user, user_invite=user_invite)

        url = reverse_lazy("authenticate:login")
        data = {"email": model.user.email.lower(), "password": password}
        response = self.client.post(url, data)

        json = response.json()
        token = self.bc.database.get("authenticate.Token", 1, dict=False)
        expected = {
            "email": model.user.email,
            "expires_at": self.bc.datetime.to_iso_string(token.expires_at),
            "token": token.key,
            "user_id": 1,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # No ProfileAcademy / white-labeled academy → no login activity is reported
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch("breathecode.activity.tasks.add_activity.delay", MagicMock())
    def test_login_uppercase_email(self):
        """Test /login"""

        password = "Pain!$%"
        user = {"email": "Konan@naruto.io", "password": make_password(password)}
        user_invite = {"email": "Konan@naruto.io", "status": "ACCEPTED", "is_email_validated": True}
        model = self.bc.database.create(user=user, user_invite=user_invite)

        url = reverse_lazy("authenticate:login")
        data = {"email": model.user.email.upper(), "password": password}
        response = self.client.post(url, data)

        json = response.json()
        token = self.bc.database.get("authenticate.Token", 1, dict=False)
        expected = {
            "email": model.user.email,
            "expires_at": self.bc.datetime.to_iso_string(token.expires_at),
            "token": token.key,
            "user_id": 1,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # No ProfileAcademy / white-labeled academy → no login activity is reported
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch("breathecode.activity.tasks.add_activity.delay", MagicMock())
    @patch.dict(
        "os.environ",
        {
            "LOGIN_RATE_LIMIT_ENABLED": "TRUE",
            "LOGIN_RATE_LIMIT_MAX_ATTEMPTS": "2",
            "LOGIN_RATE_LIMIT_WINDOW_SECONDS": "900",
        },
        clear=False,
    )
    def test_login_rate_limit_blocks_after_failures(self):
        """Test /login rate limiting after repeated bad credentials"""

        password = "Pain!$%"
        user = {"email": "Konan@naruto.io", "password": make_password(password)}
        user_invite = {"email": "Konan@naruto.io", "status": "ACCEPTED", "is_email_validated": True}
        model = self.bc.database.create(user=user, user_invite=user_invite)

        url = reverse_lazy("authenticate:login")
        data = {"email": model.user.email.lower(), "password": "wrong-password"}

        self.assertEqual(self.client.post(url, data).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(url, data).status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(url, data)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(json["silent_code"], "login-rate-limit-exceeded")
        self.bc.check.calls(activity_tasks.add_activity.delay.call_args_list, [])

    @patch("breathecode.activity.tasks.add_activity.delay", MagicMock())
    @patch.dict(
        "os.environ",
        {
            "LOGIN_RATE_LIMIT_ENABLED": "TRUE",
            "LOGIN_RATE_LIMIT_MAX_ATTEMPTS": "5",
            "LOGIN_RATE_LIMIT_WINDOW_SECONDS": "900",
        },
        clear=False,
    )
    def test_login_rate_limit_cleared_on_success(self):
        """Successful login clears the failed-attempt counters"""

        password = "Pain!$%"
        user = {"email": "Konan@naruto.io", "password": make_password(password)}
        user_invite = {"email": "Konan@naruto.io", "status": "ACCEPTED", "is_email_validated": True}
        model = self.bc.database.create(user=user, user_invite=user_invite)

        url = reverse_lazy("authenticate:login")
        bad = {"email": model.user.email.lower(), "password": "wrong-password"}
        good = {"email": model.user.email.lower(), "password": password}

        self.assertEqual(self.client.post(url, bad).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(url, bad).status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(url, good)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # After success, failures should be cleared and login should work again after one failure
        self.assertEqual(self.client.post(url, bad).status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(url, good)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("breathecode.activity.tasks.add_activity.delay", MagicMock())
    @patch.dict(
        "os.environ",
        {
            "LOGIN_RATE_LIMIT_ENABLED": "TRUE",
            "LOGIN_RATE_LIMIT_MAX_ATTEMPTS": "2",
            "LOGIN_RATE_LIMIT_WINDOW_SECONDS": "900",
        },
        clear=False,
    )
    def test_login_rate_limit_does_not_count_missing_fields(self):
        """Missing-field validation errors must not increment the rate-limit counter"""

        url = reverse_lazy("authenticate:login")
        data = {"email": "Konan@naruto.io"}

        for _ in range(5):
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertNotEqual(response.json().get("silent_code"), "login-rate-limit-exceeded")

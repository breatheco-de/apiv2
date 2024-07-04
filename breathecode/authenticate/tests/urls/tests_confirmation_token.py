"""
This file contains test over AcademyInviteView, if it change, the duck tests will deleted
"""

import os
import random
import re
from unittest.mock import MagicMock, patch, call
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase
from rest_framework import status
from rest_framework.response import Response
from django.template import loader

from breathecode.utils import capable_of
from breathecode.tests.mocks import apply_requests_post_mock

from datetime import timedelta
from django.utils import timezone
from breathecode.notify import actions

UTC_NOW = timezone.now()


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_message(message):
    request = None
    context = {"MESSAGE": message, "BUTTON": None, "LINK": os.getenv("APP_URL", "")}

    return loader.render_to_string("message.html", context, request)


def post_serializer(self, user_invite, data={}):
    return {
        "created_at": self.bc.datetime.to_iso_string(user_invite.created_at),
        "email": user_invite.email,
        "id": user_invite.id,
        "sent_at": user_invite.sent_at,
        "status": user_invite.status,
        **data,
    }


class AuthenticateJSONTestSuite(AuthTestCase):
    # When: No invites
    # Then: Return 404
    def test_not_found(self):
        """Test"""

        url = reverse_lazy("authenticate:confirmation_token", kwargs={"token": "hash"})

        response = self.client.get(url, format="json", headers={"accept": "application/json"})
        json = response.json()
        expected = {"detail": "user-invite-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)

        self.assertEqual(self.bc.database.list_of("authenticate.UserInvite"), [])

    # Given: 1 UserInvite
    # When: No email
    # Then: Return 400
    def test_no_email(self):
        """Test"""

        model = self.bc.database.create(user_invite=1)
        url = reverse_lazy("authenticate:confirmation_token", kwargs={"token": model.user_invite.token})

        response = self.client.get(url, format="json", headers={"accept": "application/json"})
        json = response.json()
        expected = {"detail": "without-email", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite),
            ],
        )

    # Given: 1 UserInvite
    # When: Email already validated
    # Then: Return 400
    def test_already_validated(self):
        """Test"""

        user_invite = {
            "email": self.bc.fake.email(),
            "is_email_validated": True,
        }
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:confirmation_token", kwargs={"token": model.user_invite.token})

        response = self.client.get(url, format="json", headers={"accept": "application/json"})
        json = response.json()
        expected = {"detail": "email-already-validated", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite),
            ],
        )

    # Given: 1 UserInvite
    # When: email and email is not validated
    # Then: Return 200
    def test_done(self):
        """Test"""

        user_invite = {"email": self.bc.fake.email()}
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:confirmation_token", kwargs={"token": model.user_invite.token})

        response = self.client.get(url, format="json", headers={"accept": "application/json"})
        json = response.json()
        expected = post_serializer(self, model.user_invite)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(model.user_invite),
                    "is_email_validated": True,
                },
            ],
        )

    # Given: 1 UserInvite
    # When: Email and email already validated
    # Then: Return 400
    def test_2_errors(self):
        """Test"""

        user_invite = {
            "is_email_validated": True,
        }
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:confirmation_token", kwargs={"token": model.user_invite.token})

        response = self.client.get(url, format="json", headers={"accept": "application/json"})
        json = response.json()
        expected = [
            {
                "detail": "without-email",
                "status_code": 400,
            },
            {
                "detail": "email-already-validated",
                "status_code": 400,
            },
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite),
            ],
        )


class AuthenticateHTMLTestSuite(AuthTestCase):
    # When: No invites
    # Then: Return 404
    def test_not_found(self):
        """Test"""

        url = reverse_lazy("authenticate:confirmation_token", kwargs={"token": "hash"})

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("user-invite-not-found")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 404)

        self.assertEqual(self.bc.database.list_of("authenticate.UserInvite"), [])

    # Given: 1 UserInvite
    # When: No email
    # Then: Return 400
    def test_no_email(self):
        """Test"""

        model = self.bc.database.create(user_invite=1)
        url = reverse_lazy("authenticate:confirmation_token", kwargs={"token": model.user_invite.token})

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("without-email.")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite),
            ],
        )

    # Given: 1 UserInvite
    # When: Email already validated
    # Then: Return 400
    def test_already_validated(self):
        """Test"""

        user_invite = {
            "email": self.bc.fake.email(),
            "is_email_validated": True,
        }
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:confirmation_token", kwargs={"token": model.user_invite.token})

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("email-already-validated.")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite),
            ],
        )

    # Given: 1 UserInvite
    # When: email and email is not validated
    # Then: Return 200
    def test_done(self):
        """Test"""

        user_invite = {"email": self.bc.fake.email()}
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:confirmation_token", kwargs={"token": model.user_invite.token})

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("Your email was validated, you can close this page.")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(model.user_invite),
                    "is_email_validated": True,
                },
            ],
        )

    # Given: 1 UserInvite
    # When: Email and email already validated
    # Then: Return 400
    def test_2_errors(self):
        """Test"""

        user_invite = {
            "is_email_validated": True,
        }
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:confirmation_token", kwargs={"token": model.user_invite.token})

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message("without-email. email-already-validated.")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite),
            ],
        )

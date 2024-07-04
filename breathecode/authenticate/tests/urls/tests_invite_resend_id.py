"""
This file contains test over AcademyInviteView, if it change, the duck tests will deleted
"""

import os
import random
import re
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from breathecode.notify import actions
from breathecode.tests.mocks import apply_requests_post_mock
from breathecode.utils import capable_of

from ..mixins.new_auth_test_case import AuthTestCase

UTC_NOW = timezone.now()


def post_serializer(self, user_invite, data={}):
    return {
        "created_at": self.bc.datetime.to_iso_string(user_invite.created_at),
        "email": user_invite.email,
        "id": user_invite.id,
        "sent_at": user_invite.sent_at,
        "status": user_invite.status,
        **data,
    }


class AuthenticateTestSuite(AuthTestCase):
    # When: No invites
    # Then: Return 404
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_not_found(self):
        """Test"""
        url = reverse_lazy("authenticate:invite_resend_id", kwargs={"invite_id": 1})

        response = self.client.put(url)
        json = response.json()
        expected = {"detail": "user-invite-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)

        self.assertEqual(self.bc.database.list_of("authenticate.UserInvite"), [])
        self.bc.check.calls(actions.send_email_message.call_args_list, [])

    # Given: 1 UserInvite
    # When: No email
    # Then: Return 400
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_no_email(self):
        """Test"""

        model = self.bc.database.create(user_invite=1)
        url = reverse_lazy("authenticate:invite_resend_id", kwargs={"invite_id": 1})

        response = self.client.put(url)
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
        self.bc.check.calls(actions.send_email_message.call_args_list, [])

    # Given: 1 UserInvite
    # When: email, status PENDING and sent_at is None
    # Then: Return 200
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_sent_at_none(self):
        """Test"""

        user_invite = {"email": self.bc.fake.email()}
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:invite_resend_id", kwargs={"invite_id": 1})

        response = self.client.put(url)
        json = response.json()
        expected = post_serializer(
            self,
            model.user_invite,
            data={
                "sent_at": self.bc.datetime.to_iso_string(UTC_NOW),
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(model.user_invite),
                    "sent_at": UTC_NOW,
                },
            ],
        )

        self.bc.check.calls(
            actions.send_email_message.call_args_list,
            [
                call(
                    "welcome_academy",
                    model.user_invite.email,
                    {
                        "email": model.user_invite.email,
                        "subject": "Invitation to join 4Geeks",
                        "LINK": (
                            os.getenv("API_URL", "")
                            + "/v1/auth/member/invite/"
                            + model.user_invite.token
                            + "?callback=https%3A%2F%2Fadmin.4geeks.com"
                        ),
                        "FIST_NAME": model.user_invite.first_name,
                    },
                    academy=None,
                )
            ],
        )

    # Given: 1 UserInvite
    # When: email, status PENDING and sent_at gt 1 day from now
    # Then: Return 200
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_sent_at_gt_a_day(self):
        """Test"""

        user_invite = {
            "email": self.bc.fake.email(),
            "sent_at": UTC_NOW - timedelta(days=1, seconds=random.randint(1, 3600 * 24 * 7)),
        }
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:invite_resend_id", kwargs={"invite_id": 1})

        response = self.client.put(url)
        json = response.json()
        expected = post_serializer(
            self,
            model.user_invite,
            data={
                "sent_at": self.bc.datetime.to_iso_string(UTC_NOW),
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(model.user_invite),
                    "sent_at": UTC_NOW,
                },
            ],
        )

        self.bc.check.calls(
            actions.send_email_message.call_args_list,
            [
                call(
                    "welcome_academy",
                    model.user_invite.email,
                    {
                        "email": model.user_invite.email,
                        "subject": "Invitation to join 4Geeks",
                        "LINK": (
                            os.getenv("API_URL", "")
                            + "/v1/auth/member/invite/"
                            + model.user_invite.token
                            + "?callback=https%3A%2F%2Fadmin.4geeks.com"
                        ),
                        "FIST_NAME": model.user_invite.first_name,
                    },
                    academy=None,
                )
            ],
        )

    # Given: 1 UserInvite
    # When: email, status PENDING and sent_at lt 1 day from now
    # Then: Return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_sent_at_lt_a_day(self):
        """Test"""

        user_invite = {
            "email": self.bc.fake.email(),
            "sent_at": UTC_NOW - timedelta(seconds=random.randint(0, (60 * 10) - 1)),
        }
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:invite_resend_id", kwargs={"invite_id": 1})

        response = self.client.put(url)
        json = response.json()
        expected = {"detail": "sent-at-diff-less-10-minutes", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite),
            ],
        )
        self.bc.check.calls(actions.send_email_message.call_args_list, [])

    # Given: 1 UserInvite
    # When: email, invite answered and sent_at is None, email validated
    # Then: Return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_invite_answered__email_validated(self):
        """Test"""

        user_invite = {
            "email": self.bc.fake.email(),
            "status": random.choice(["ACCEPTED", "REJECTED"]),
            "is_email_validated": True,
        }
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:invite_resend_id", kwargs={"invite_id": 1})

        response = self.client.put(url)
        json = response.json()
        expected = {"detail": f'user-already-{user_invite["status"].lower()}', "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite),
            ],
        )
        self.bc.check.calls(actions.send_email_message.call_args_list, [])

    # Given: 1 UserInvite
    # When: email, invite answered and sent_at is None, email not validated
    # Then: Return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_invite_answered__email_not_validated(self):
        """Test"""

        user_invite = {
            "email": self.bc.fake.email(),
            "status": random.choice(["ACCEPTED", "REJECTED"]),
            "is_email_validated": False,
        }
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:invite_resend_id", kwargs={"invite_id": 1})

        response = self.client.put(url)
        json = response.json()
        expected = post_serializer(
            self,
            model.user_invite,
            data={
                "sent_at": self.bc.datetime.to_iso_string(UTC_NOW),
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(model.user_invite),
                    "sent_at": UTC_NOW,
                }
            ],
        )

        self.bc.check.calls(
            actions.send_email_message.call_args_list,
            [
                call(
                    "verify_email",
                    model.user_invite.email,
                    {
                        "SUBJECT": "Verify your 4Geeks account",
                        "LINK": os.getenv("API_URL", "") + f"/v1/auth/confirmation/{model.user_invite.token}",
                    },
                    academy=None,
                ),
            ],
        )

    # Given: 1 UserInvite
    # When: email, status is WAITING_LIST and sent_at is None
    # Then: Return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_invite_in_waiting_list(self):
        """Test"""

        user_invite = {
            "email": self.bc.fake.email(),
            "status": "WAITING_LIST",
        }
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:invite_resend_id", kwargs={"invite_id": 1})

        response = self.client.put(url)
        json = response.json()
        expected = {"detail": f'user-already-{user_invite["status"].lower()}', "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite),
            ],
        )
        self.bc.check.calls(actions.send_email_message.call_args_list, [])

    # Given: 1 UserInvite
    # When: 3 errors at the same time
    # Then: Return 400
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_return_3_errors(self):
        """Test"""

        user_invite = {
            "sent_at": UTC_NOW - timedelta(seconds=random.randint(0, (60 * 10) - 1)),
            "status": random.choice(["ACCEPTED", "REJECTED"]),
            "is_email_validated": True,
        }
        model = self.bc.database.create(user_invite=user_invite)
        url = reverse_lazy("authenticate:invite_resend_id", kwargs={"invite_id": 1})

        response = self.client.put(url)
        json = response.json()
        expected = [
            {
                "detail": f"user-already-{model.user_invite.status.lower()}",
                "status_code": 400,
            },
            {
                "detail": "without-email",
                "status_code": 400,
            },
            {
                "detail": "sent-at-diff-less-10-minutes",
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
        self.bc.check.calls(actions.send_email_message.call_args_list, [])

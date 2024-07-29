import datetime
from logging import Logger
from random import choice
from unittest.mock import MagicMock, call, patch

# from datetime import datetime
import pytest
from django.utils import timezone

from breathecode.authenticate.tasks import async_accept_user_from_waiting_list
from breathecode.notify import actions as notify_actions

from ..mixins.new_auth_test_case import AuthTestCase


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.authenticate.tasks.create_user_from_invite.apply_async", MagicMock())
    monkeypatch.setattr("breathecode.authenticate.tasks.create_user_from_invite.delay", MagicMock())
    monkeypatch.setattr("breathecode.authenticate.tasks.async_validate_email_invite.delay", MagicMock())

    yield


class ModelProfileAcademyTestSuite(AuthTestCase):
    """
    🔽🔽🔽 With zero UserInvite
    """

    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_with_zero_user_invite(self):
        result = async_accept_user_from_waiting_list(1)

        self.assertEqual(result, None)
        self.assertEqual(Logger.error.call_args_list, [call("UserInvite 1 not found")])
        self.assertEqual(self.bc.database.list_of("auth.User"), [])
        self.assertEqual(self.bc.database.list_of("authenticate.UserInvite"), [])
        self.assertEqual(notify_actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 With one UserInvite
    """

    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_with_one_user_invite(self):
        model = self.bc.database.create(user_invite=1)

        result = async_accept_user_from_waiting_list(1)

        self.assertEqual(result, None)
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(self.bc.database.list_of("auth.User"), [])
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(model.user_invite),
                    "process_message": "Can't determine the user email",
                    "process_status": "ERROR",
                    "status": "ACCEPTED",
                },
            ],
        )

        self.assertEqual(notify_actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 With one UserInvite, with email
    """

    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_with_one_user_invite__with_email(self):
        user_invite = {"email": self.bc.fake.email()}
        model = self.bc.database.create(user_invite=user_invite)

        start = timezone.now()
        result = async_accept_user_from_waiting_list(1)
        end = timezone.now()

        self.assertEqual(result, None)
        self.assertEqual(Logger.error.call_args_list, [])

        users = [
            x
            for x in self.bc.database.list_of("auth.User")
            if self.bc.check.datetime_in_range(start, end, x["date_joined"]) or x.pop("date_joined")
        ]

        self.assertEqual(
            users,
            [
                {
                    "email": model.user_invite.email,
                    "first_name": "",
                    "id": 1,
                    "is_active": True,
                    "is_staff": False,
                    "is_superuser": False,
                    "last_login": None,
                    "last_name": "",
                    "password": "",
                    "username": model.user_invite.email,
                }
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(model.user_invite),
                    "process_message": "Registered as User with id 1",
                    "process_status": "DONE",
                },
            ],
        )

        self.assertEqual(notify_actions.send_email_message.call_args_list, [])

    """
    🔽🔽🔽 With one UserInvite, with email
    """

    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_with_one_user_invite__with_email(self):
        user_invite = {"email": self.bc.fake.email()}
        model = self.bc.database.create(user_invite=user_invite)

        start = timezone.now()
        result = async_accept_user_from_waiting_list(1)
        end = timezone.now()

        self.assertEqual(result, None)
        self.assertEqual(Logger.error.call_args_list, [])

        users = [
            x
            for x in self.bc.database.list_of("auth.User")
            if self.bc.check.datetime_in_range(start, end, x["date_joined"]) or x.pop("date_joined")
        ]

        self.assertEqual(
            users,
            [
                {
                    "email": model.user_invite.email,
                    "first_name": "",
                    "id": 1,
                    "is_active": True,
                    "is_staff": False,
                    "is_superuser": False,
                    "last_login": None,
                    "last_name": "",
                    "password": "",
                    "username": model.user_invite.email,
                }
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(model.user_invite),
                    "process_message": "Registered as User with id 1",
                    "process_status": "DONE",
                    "status": "ACCEPTED",
                    "user_id": 1,
                },
            ],
        )

        token = self.bc.database.get("authenticate.Token", 1, dict=False)

        self.assertEqual(
            str(notify_actions.send_email_message.call_args_list),
            str(
                [
                    call(
                        "pick_password",
                        model.user_invite.email,
                        {
                            "SUBJECT": "Set your password at 4Geeks",
                            "LINK": f"http://localhost:8000/v1/auth/password/{model.user_invite.token}",
                        },
                        academy=None,
                    )
                ]
            ),
        )

    """
    🔽🔽🔽 With one UserInvite, with email
    """

    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_with_one_user_invite__with_email__user_already_exists(self):
        email = self.bc.fake.email()
        user = {"email": email}
        user_invite = {"email": email}
        model = self.bc.database.create(user=user, user_invite=user_invite)

        start = timezone.now()
        result = async_accept_user_from_waiting_list(1)
        end = timezone.now()

        self.assertEqual(result, None)
        self.assertEqual(Logger.error.call_args_list, [])

        self.assertEqual(
            self.bc.database.list_of("auth.User"),
            [
                self.bc.format.to_dict(model.user),
            ],
        )

        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(model.user_invite),
                    "process_message": "User already exists with the id 1",
                    "process_status": "DONE",
                    "status": "ACCEPTED",
                },
            ],
        )

        self.assertEqual(str(notify_actions.send_email_message.call_args_list), str([]))

"""
Test /academy/cohort
"""

from unittest.mock import MagicMock, call, patch

from django.core.management.base import OutputWrapper

from ....management.commands.confirm_no_saas_emails import Command
from ...mixins.new_auth_test_case import AuthTestCase


class AcademyCohortTestSuite(AuthTestCase):
    """
    🔽🔽🔽 With zero Profile
    """

    # When: No invites
    # Then: Shouldn't do anything
    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_0_invites(self):
        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of("authenticate.UserInvite"), [])
        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("Successfully confirmed 0 invites"),
            ],
        )

    # Given: 2 UserInvite, 1 Academy
    # When: email is not validated and academy is not available as saas
    # Then: validate all emails
    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_2_invites__no_saas__academy(self):
        academy = {"available_as_saas": False}
        user_invites = [
            {
                "email": self.bc.fake.email(),
                "is_email_validated": False,
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(user_invite=user_invites, academy=academy)

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(model.user_invite[0]),
                    "is_email_validated": True,
                },
                {
                    **self.bc.format.to_dict(model.user_invite[1]),
                    "is_email_validated": True,
                },
            ],
        )
        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("Successfully confirmed 2 invites"),
            ],
        )

    # Given: 2 UserInvite, 1 Academy, 1 Cohort
    # When: email is not validated and cohort from an academy is not available as saas
    # Then: validate all emails
    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_2_invites__no_saas__cohort(self):
        academy = {"available_as_saas": False}
        user_invites = [
            {
                "academy_id": None,
                "email": self.bc.fake.email(),
                "is_email_validated": False,
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(user_invite=user_invites, academy=academy, cohort=1)

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(model.user_invite[0]),
                    "is_email_validated": True,
                },
                {
                    **self.bc.format.to_dict(model.user_invite[1]),
                    "is_email_validated": True,
                },
            ],
        )
        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("Successfully confirmed 2 invites"),
            ],
        )

    # Given: 2 UserInvite, 1 Academy
    # When: email is not validated and academy is not available as saas
    # Then: Shouldn't do anything
    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_2_invites__saas__academy(self):
        academy = {"available_as_saas": True}
        user_invites = [
            {
                "email": self.bc.fake.email(),
                "is_email_validated": False,
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(user_invite=user_invites, academy=academy)

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite[0]),
                self.bc.format.to_dict(model.user_invite[1]),
            ],
        )

        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("Successfully confirmed 0 invites"),
            ],
        )

    # Given: 2 UserInvite, 1 Academy, 1 Cohort
    # When: email is not validated and cohort from an academy is not available as saas
    # Then: Shouldn't do anything
    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_2_invites__saas__cohort(self):
        academy = {"available_as_saas": True}
        user_invites = [
            {
                "academy_id": None,
                "email": self.bc.fake.email(),
                "is_email_validated": False,
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(user_invite=user_invites, academy=academy, cohort=1)

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite[0]),
                self.bc.format.to_dict(model.user_invite[1]),
            ],
        )

        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("Successfully confirmed 0 invites"),
            ],
        )

    # Given: 2 UserInvite, 1 Academy
    # When: email is validated and academy is not available as saas
    # Then: Shouldn't do anything
    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_2_invites__email_already_validated__no_saas__academy(self):
        academy = {"available_as_saas": False}
        user_invites = [
            {
                "email": self.bc.fake.email(),
                "is_email_validated": True,
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(user_invite=user_invites, academy=academy)

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite[0]),
                self.bc.format.to_dict(model.user_invite[1]),
            ],
        )

        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("Successfully confirmed 0 invites"),
            ],
        )

    # Given: 2 UserInvite, 1 Academy, 1 Cohort
    # When: email is validated and cohort from an academy is not available as saas
    # Then: Shouldn't do anything
    @patch("django.core.management.base.OutputWrapper.write", MagicMock())
    def test_2_invites__email_already_validated__no_saas__cohort(self):
        academy = {"available_as_saas": False}
        user_invites = [
            {
                "academy_id": None,
                "email": self.bc.fake.email(),
                "is_email_validated": True,
            }
            for _ in range(2)
        ]

        model = self.bc.database.create(user_invite=user_invites, academy=academy, cohort=1)

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite[0]),
                self.bc.format.to_dict(model.user_invite[1]),
            ],
        )

        self.assertEqual(
            OutputWrapper.write.call_args_list,
            [
                call("Successfully confirmed 0 invites"),
            ],
        )

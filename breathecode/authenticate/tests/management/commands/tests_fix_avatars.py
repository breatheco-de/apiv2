"""
Test /academy/cohort
"""

import os
import random
import logging
from unittest.mock import MagicMock, patch, call
from ...mixins.new_auth_test_case import AuthTestCase
from ....management.commands.fix_avatars import Command


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class AcademyCohortTestSuite(AuthTestCase):
    """
    🔽🔽🔽 With zero Profile
    """

    @patch("logging.Logger.info", MagicMock())
    def test_with_zero_profiles(self):
        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(self.bc.database.list_of("authenticate.Profile"), [])
        self.assertEqual(logging.Logger.info.call_args_list, [call("Fixing 0 avatars")])

    """
    🔽🔽🔽 With two Profile, avatar_url is null
    """

    @patch("logging.Logger.info", MagicMock())
    def test_with_two_profiles__avatar_url_is_null(self):
        model = self.bc.database.create(profile=2)
        logging.Logger.info.call_args_list = []

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            self.bc.format.to_dict(model.profile),
        )
        self.assertEqual(logging.Logger.info.call_args_list, [call("Fixing 0 avatars")])

    """
    🔽🔽🔽 With two Profile, avatar_url is set, does'nt match with API_URL
    """

    @patch("logging.Logger.info", MagicMock())
    def test_with_two_profiles__avatar_url_is_set__does_not_match_with_api_url(self):
        profiles = [{"avatar_url": self.bc.fake.url()[0:-1]} for _ in range(0, 2)]
        model = self.bc.database.create(profile=profiles)
        logging.Logger.info.call_args_list = []

        command = Command()
        result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            self.bc.format.to_dict(model.profile),
        )
        self.assertEqual(logging.Logger.info.call_args_list, [call("Fixing 0 avatars")])

    """
    🔽🔽🔽 With two Profile, avatar_url is set, match with API_URL
    """

    @patch("logging.Logger.info", MagicMock())
    def test_with_two_profiles__avatar_url_is_set__match_with_api_url(self):
        api_url = self.bc.fake.url()[0:-1]
        latest_avatar_url = api_url + "/static/img/avatar.png"
        profiles = [{"avatar_url": latest_avatar_url} for _ in range(0, 2)]
        model = self.bc.database.create(profile=profiles)

        logging.Logger.info.call_args_list = []

        random_numbers = [random.randint(1, 21) for _ in range(0, 2)]
        with patch("random.randint") as randint_mock:
            randint_mock.side_effect = random_numbers

            with patch("os.getenv") as getenv_mock:
                getenv_mock.side_effect = apply_get_env({"API_URL": api_url})

                command = Command()
                result = command.handle()

                self.assertEqual(os.getenv.call_args_list, [call("API_URL", "")])

            self.assertEqual(random.randint.call_args_list, [call(1, 21), call(1, 21)])

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("authenticate.Profile"),
            [
                {
                    **self.bc.format.to_dict(model.profile[0]),
                    "avatar_url": api_url + f"/static/img/avatar-{random_numbers[0]}.png",
                },
                {
                    **self.bc.format.to_dict(model.profile[1]),
                    "avatar_url": api_url + f"/static/img/avatar-{random_numbers[1]}.png",
                },
            ],
        )
        self.assertEqual(logging.Logger.info.call_args_list, [call("Fixing 2 avatars")])

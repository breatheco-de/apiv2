import logging
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, call, mock_open, patch

from breathecode.services.google_cloud.credentials import resolve_credentials

logger = logging.getLogger("breathecode.setup")


class CredentialsTestCase(TestCase):

    @patch("builtins.open", mock_open(read_data="{}\n"))
    @patch("os.path.exists", MagicMock(return_value=False))
    @patch.object(logger, "error")
    def test_resolve_credentials__credentials_file_not_exists__without_env(self, logger_mock):
        from os.path import exists as exists_mock

        open_mock = open

        if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

        if "GOOGLE_SERVICE_KEY" in os.environ:
            del os.environ["GOOGLE_SERVICE_KEY"]

        result = resolve_credentials()

        self.assertEqual(result, False)
        self.assertEqual(open_mock.mock_calls, [])
        self.assertEqual(exists_mock.mock_calls, [])
        self.assertEqual(logger_mock.mock_calls, [call("GOOGLE_APPLICATION_CREDENTIALS is not set")])

        self.assertTrue("GOOGLE_APPLICATION_CREDENTIALS" not in os.environ)

    @patch("builtins.open", mock_open(read_data="{}\n"))
    @patch("os.path.exists", MagicMock(return_value=False))
    @patch.object(logger, "error")
    def test_resolve_credentials__credentials_file_not_exists__without_second_env(self, logger_mock):
        from os.path import exists as exists_mock

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./.lacey_mosley.json"

        if "GOOGLE_SERVICE_KEY" in os.environ:
            del os.environ["GOOGLE_SERVICE_KEY"]

        open_mock = open
        result = resolve_credentials()

        self.assertEqual(result, False)
        self.assertEqual(open_mock.mock_calls, [])
        self.assertEqual(
            exists_mock.mock_calls,
            [
                call(Path(os.path.join(os.getcwd(), ".lacey_mosley.json"))),
            ],
        )

        self.assertEqual(logger_mock.mock_calls, [call("GOOGLE_SERVICE_KEY is not set")])

        self.assertEqual(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], str(Path(os.path.join(os.getcwd(), ".lacey_mosley.json")))
        )

    @patch("builtins.open", mock_open(read_data="{}\n"))
    @patch("os.path.exists", MagicMock(return_value=False))
    @patch.object(logger, "error")
    def test_resolve_credentials__credentials_file_not_exists__with_env(self, logger_mock):
        from os.path import exists as exists_mock

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./.lacey_mosley.json"
        os.environ["GOOGLE_SERVICE_KEY"] = "{}\n"
        open_mock = open

        result = resolve_credentials()

        self.assertEqual(result, True)
        self.assertEqual(
            open_mock.mock_calls,
            [
                call(Path(os.path.join(os.getcwd(), ".lacey_mosley.json")), "w"),
                call().__enter__(),
                call().write("{}\n"),
                call().__exit__(None, None, None),
            ],
        )

        self.assertEqual(
            exists_mock.mock_calls,
            [
                call(Path(os.path.join(os.getcwd(), ".lacey_mosley.json"))),
            ],
        )

        self.assertEqual(logger_mock.mock_calls, [])
        self.assertEqual(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], str(Path(os.path.join(os.getcwd(), ".lacey_mosley.json")))
        )

    @patch("builtins.open", mock_open(read_data="{}\n"))
    @patch("os.path.exists", MagicMock(return_value=True))
    @patch.object(logger, "error")
    def test_resolve_credentials__credentials_file_exists__with_env(self, logger_mock):
        from os.path import exists as exists_mock

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./.lacey_mosley.json"
        os.environ["GOOGLE_SERVICE_KEY"] = "{}\n"
        open_mock = open

        result = resolve_credentials()

        self.assertEqual(result, True)
        self.assertEqual(open_mock.mock_calls, [])
        self.assertEqual(
            exists_mock.mock_calls,
            [
                call(Path(os.path.join(os.getcwd(), ".lacey_mosley.json"))),
            ],
        )

        self.assertEqual(logger_mock.mock_calls, [])
        self.assertEqual(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], str(Path(os.path.join(os.getcwd(), ".lacey_mosley.json")))
        )

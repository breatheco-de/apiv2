from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch, MagicMock, call, mock_open
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    MAILGUN_PATH,
    MAILGUN_INSTANCES,
    apply_mailgun_requests_post_mock,
    SLACK_PATH,
    SLACK_INSTANCES,
    apply_slack_requests_request_mock,
    REQUESTS_PATH,
    REQUESTS_INSTANCES,
    apply_requests_get_mock,
    LOGGING_PATH,
    LOGGING_INSTANCES,
    apply_logging_logger_mock,
)
from ...mixins import MonitoringTestCase
from ....management.commands.monitor import Command


class AcademyCohortTestSuite(MonitoringTestCase):
    """
    🔽🔽🔽 With bad entity 🔽🔽🔽
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://potato.io", {})]))
    def tests_monitor_without_entity(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        mock_breathecode = REQUESTS_INSTANCES["get"]
        mock_breathecode.call_args_list = []

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(), None)
        self.assertEqual(command.stdout.write.call_args_list, [])
        self.assertEqual(command.stderr.write.call_args_list, [call("Entity arguments is not set")])
        self.assertEqual(self.all_endpoint_dict(), [])

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(mock_breathecode.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://potato.io", {})]))
    def tests_monitor_with_bad_entity(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        mock_breathecode = REQUESTS_INSTANCES["get"]
        mock_breathecode.call_args_list = []

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="they-killed-kenny"), None)
        self.assertEqual(command.stdout.write.call_args_list, [])
        self.assertEqual(command.stderr.write.call_args_list, [call("Entity not found")])
        self.assertEqual(self.all_endpoint_dict(), [])

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(mock_breathecode.call_args_list, [])

    # """
    # 🔽🔽🔽 App entity 🔽🔽🔽
    # """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_without_application(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 0 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(self.all_application_dict(), [])
        self.assertEqual(self.all_endpoint_dict(), [])

        import requests

        mock_breathecode = requests.get
        mock_breathecode.call_args_list = []

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(mock_breathecode.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_without_endpoints(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        model = self.generate_models(application=True)
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )
        self.assertEqual(self.all_endpoint_dict(), [])

        import requests

        mock_breathecode = requests.get
        mock_breathecode.call_args_list = []

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(mock_breathecode.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_with_bad_endpoint_paused_until(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        endpoint_kwargs = {
            "url": "https://potato.io",
            "paused_until": timezone.now() + timedelta(minutes=2),
        }

        model = self.generate_models(application=True, endpoint=True, endpoint_kwargs=endpoint_kwargs)
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        self.assertEqual(
            self.all_endpoint_dict(),
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "severity_level": 0,
                    "status_text": None,
                }
            ],
        )

        import requests

        mock_breathecode = requests.get
        mock_breathecode.call_args_list = []

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(mock_breathecode.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_with_endpoint_paused_until(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        endpoint_kwargs = {
            "url": "https://potato.io",
            "paused_until": timezone.now(),
        }

        model = self.generate_models(application=True, endpoint=True, endpoint_kwargs=endpoint_kwargs)
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": None,
                    "severity_level": 5,
                    "status_text": "Status withing the 2xx range",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get
        mock_breathecode.call_args_list = []

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(mock_breathecode.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_with_bad_application_paused_until(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        endpoint_kwargs = {
            "url": "https://potato.io",
            "paused_until": timezone.now() + timedelta(minutes=2),
        }

        model = self.generate_models(application=True, endpoint=True, endpoint_kwargs=endpoint_kwargs)
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        self.assertEqual(
            self.all_endpoint_dict(),
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "severity_level": 0,
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(mock_breathecode.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(100, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_status_100(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        model = self.generate_models(application=True, endpoint=True, endpoint_kwargs={"url": "https://potato.io"})
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": "{}",
                    "severity_level": 0,
                    "status": "MINOR",
                    "status_code": 100,
                    "status_text": "Uknown status code, lower than 200",
                }
            ],
        )

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])

        import requests

        mock_breathecode = requests.get

        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_status_200(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        model = self.generate_models(application=True, endpoint=True, endpoint_kwargs={"url": "https://potato.io"})
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": None,
                    "severity_level": 5,
                    "status_text": "Status withing the 2xx range",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://potato.io", "is not ok")]))
    def tests_monitor_with_entity_apps_status_200_with_bad_regex(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        endpoint_kwargs = {"url": "https://potato.io", "test_pattern": "^ok$"}

        model = self.generate_models(application=True, endpoint=True, endpoint_kwargs=endpoint_kwargs)
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": "is not ok",
                    "severity_level": 5,
                    "status": "MINOR",
                    "status_text": "Status is 200 but regex ^ok$ was rejected",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://potato.io", "ok")]))
    def tests_monitor_with_entity_apps_status_200_with_regex(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        endpoint_kwargs = {"url": "https://potato.io", "test_pattern": "^ok$"}

        model = self.generate_models(application=True, endpoint=True, endpoint_kwargs=endpoint_kwargs)
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "severity_level": 5,
                    "status_text": "Status withing the 2xx range",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(300, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_status_300(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        model = self.generate_models(application=True, endpoint=True, endpoint_kwargs={"url": "https://potato.io"})
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": "{}",
                    "severity_level": 5,
                    "status": "MINOR",
                    "status_code": 300,
                    "status_text": "Status in the 3xx range, maybe a cached reponse?",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(400, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_status_400(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        model = self.generate_models(application=True, endpoint=True, endpoint_kwargs={"url": "https://potato.io"})
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": "{}",
                    "severity_level": 100,
                    "status": "CRITICAL",
                    "status_code": 400,
                    "status_text": "Status above 399",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(404, "https://potato.io", "ok")]))
    def tests_monitor_with_entity_apps_status_404_with_regex(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        endpoint_kwargs = {"url": "https://potato.io", "test_pattern": "^ok$"}

        model = self.generate_models(application=True, endpoint=True, endpoint_kwargs=endpoint_kwargs)
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": "ok",
                    "severity_level": 100,
                    "status": "CRITICAL",
                    "status_code": 404,
                    "status_text": "Status above 399",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(500, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_status_500(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        model = self.generate_models(application=True, endpoint=True, endpoint_kwargs={"url": "https://potato.io"})
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": "{}",
                    "severity_level": 100,
                    "status": "CRITICAL",
                    "status_code": 500,
                    "status_text": "Status above 399",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(500, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_status_500_with_email(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        application_kwargs = {"notify_email": "pokemon@potato.io"}

        endpoint_kwargs = {"url": "https://potato.io"}

        model = self.generate_models(
            application=True, endpoint=True, application_kwargs=application_kwargs, endpoint_kwargs=endpoint_kwargs
        )
        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": "{}",
                    "severity_level": 100,
                    "status": "CRITICAL",
                    "status_code": 500,
                    "status_text": "Status above 399",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(len(mock_mailgun.call_args_list), 1)
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(500, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_status_500_with_notify_slack_channel_without_slack_team(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        endpoint_kwargs = {"url": "https://potato.io"}

        model = self.generate_models(
            application=True,
            endpoint=True,
            slack_channel=True,
            credentials_slack=True,
            # academy=True, slack_team=True,
            endpoint_kwargs=endpoint_kwargs,
        )

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": "{}",
                    "severity_level": 100,
                    "status": "CRITICAL",
                    "status_code": 500,
                    "status_text": "Status above 399",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(500, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_status_500_with_notify_slack_channel_without_slack_models(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        endpoint_kwargs = {"url": "https://potato.io"}

        model = self.generate_models(
            application=True, endpoint=True, slack_channel=True, credentials_slack=True, endpoint_kwargs=endpoint_kwargs
        )

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": "{}",
                    "severity_level": 100,
                    "status": "CRITICAL",
                    "status_code": 500,
                    "status_text": "Status above 399",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(500, "https://potato.io", {})]))
    def tests_monitor_with_entity_apps_status_500_with_notify_slack_channel_with_slack_models(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        endpoint_kwargs = {"url": "https://potato.io"}

        model = self.generate_models(
            application=True,
            endpoint=True,
            slack_channel=True,
            credentials_slack=True,
            slack_team=True,
            academy=True,
            endpoint_kwargs=endpoint_kwargs,
        )

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="apps"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 apps for diagnostic")])
        self.assertEqual(command.stderr.write.call_args_list, [])
        self.assertEqual(
            self.all_application_dict(),
            [
                {
                    **self.model_to_dict(model, "application"),
                }
            ],
        )

        endpoints = [
            {**endpoint, "last_check": None}
            for endpoint in self.all_endpoint_dict()
            if self.assertDatetime(endpoint["last_check"])
        ]
        self.assertEqual(
            endpoints,
            [
                {
                    **self.model_to_dict(model, "endpoint"),
                    "frequency_in_minutes": 30.0,
                    "response_text": "{}",
                    "severity_level": 100,
                    "status": "CRITICAL",
                    "status_code": 500,
                    "status_text": "Status above 399",
                }
            ],
        )

        import requests

        mock_breathecode = requests.get

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(len(mock_slack.call_args_list), 1)
        self.assertEqual(
            mock_breathecode.call_args_list,
            [call("https://potato.io", headers={"User-Agent": "BreathecodeMonitoring/1.0"}, timeout=2)],
        )

    """
    🔽🔽🔽 Scripts entity 🔽🔽🔽
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    def tests_monitor_with_entity_scripts_without_data(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="scripts"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 0 scripts for execution")])
        self.assertEqual(command.stderr.write.call_args_list, [])

        self.assertEqual(self.all_monitor_script_dict(), [])
        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    def tests_monitor_with_entity_scripts_doesnt_exist_or_not_have_body(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        model = self.generate_models(monitor_script=True)

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="scripts"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 scripts for execution")])
        self.assertEqual(command.stderr.write.call_args_list, [])

        monitor_scripts = [
            {**x, "last_run": None} for x in self.all_monitor_script_dict() if self.assertDatetime(x["last_run"])
        ]

        self.assertEqual(
            monitor_scripts,
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                    "status_code": 1,
                    "status": "CRITICAL",
                    "special_status_text": "Script not found or its body is empty: None",
                    "response_text": "Script not found or its body is empty: None",
                },
            ],
        )

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    def tests_monitor_with_entity_scripts_in_body_with_successful_execution(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        monitor_script_kwargs = {"script_body": "print('aaaa')"}

        model = self.generate_models(monitor_script=True, monitor_script_kwargs=monitor_script_kwargs)

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="scripts"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 scripts for execution")])
        self.assertEqual(command.stderr.write.call_args_list, [])

        monitor_scripts = [
            {**x, "last_run": None} for x in self.all_monitor_script_dict() if self.assertDatetime(x["last_run"])
        ]
        self.assertEqual(
            monitor_scripts,
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                    "response_text": "aaaa\n",
                    "status_code": 0,
                    "special_status_text": "OK",
                }
            ],
        )

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    def tests_monitor_with_entity_scripts_in_body_with_minor_error(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        monitor_script_kwargs = {
            "script_body": "\n".join(
                [
                    "from breathecode.utils import ScriptNotification",
                    "raise ScriptNotification('thus spoke kishibe rohan', status='MINOR')",
                ]
            )
        }

        model = self.generate_models(monitor_script=True, monitor_script_kwargs=monitor_script_kwargs)

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="scripts"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 scripts for execution")])
        self.assertEqual(command.stderr.write.call_args_list, [])

        monitor_scripts = [
            {**x, "last_run": None} for x in self.all_monitor_script_dict() if self.assertDatetime(x["last_run"])
        ]
        self.assertEqual(
            monitor_scripts,
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                    "response_text": monitor_scripts[0]["response_text"],
                    "status": "MINOR",
                    "status_code": 1,
                }
            ],
        )

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    def tests_monitor_with_entity_scripts_in_body_with_critical_error(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        monitor_script_kwargs = {
            "script_body": "\n".join(
                [
                    "from breathecode.utils import ScriptNotification",
                    "raise ScriptNotification('thus spoke kishibe rohan', status='CRITICAL')",
                ]
            )
        }

        model = self.generate_models(monitor_script=True, monitor_script_kwargs=monitor_script_kwargs)

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="scripts"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 scripts for execution")])
        self.assertEqual(command.stderr.write.call_args_list, [])

        monitor_scripts = [
            {**x, "last_run": None} for x in self.all_monitor_script_dict() if self.assertDatetime(x["last_run"])
        ]
        self.assertEqual(
            monitor_scripts,
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                    "response_text": monitor_scripts[0]["response_text"],
                    "status": "CRITICAL",
                    "status_code": 1,
                }
            ],
        )

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch("builtins.open", mock_open(read_data="print('aaaa')"))
    def tests_monitor_with_entity_scripts_in_file_with_successful_execution(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        monitor_script_kwargs = {"script_slug": "they-killed-kenny"}

        model = self.generate_models(monitor_script=True, monitor_script_kwargs=monitor_script_kwargs)

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="scripts"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 scripts for execution")])
        self.assertEqual(command.stderr.write.call_args_list, [])

        monitor_scripts = [
            {**x, "last_run": None} for x in self.all_monitor_script_dict() if self.assertDatetime(x["last_run"])
        ]
        self.assertEqual(
            monitor_scripts,
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                    "response_text": "aaaa\n",
                    "status_code": 0,
                    "special_status_text": "OK",
                }
            ],
        )

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(
        "builtins.open",
        mock_open(
            read_data="\n".join(
                [
                    "from breathecode.utils import ScriptNotification",
                    "raise ScriptNotification('thus spoke kishibe rohan', status='MINOR')",
                ]
            )
        ),
    )
    def tests_monitor_with_entity_scripts_in_file_with_minor_error(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        monitor_script_kwargs = {"script_slug": "they-killed-kenny"}

        model = self.generate_models(monitor_script=True, monitor_script_kwargs=monitor_script_kwargs)

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="scripts"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 scripts for execution")])
        self.assertEqual(command.stderr.write.call_args_list, [])

        monitor_scripts = [
            {**x, "last_run": None} for x in self.all_monitor_script_dict() if self.assertDatetime(x["last_run"])
        ]
        self.assertEqual(
            monitor_scripts,
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                    "response_text": monitor_scripts[0]["response_text"],
                    "status": "MINOR",
                    "status_code": 1,
                }
            ],
        )

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(
        "builtins.open",
        mock_open(
            read_data="\n".join(
                [
                    "from breathecode.utils import ScriptNotification",
                    "raise ScriptNotification('thus spoke kishibe rohan', status='CRITICAL')",
                ]
            )
        ),
    )
    def tests_monitor_with_entity_scripts_in_file_with_critical_error(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        monitor_script_kwargs = {"script_slug": "they-killed-kenny"}

        model = self.generate_models(monitor_script=True, monitor_script_kwargs=monitor_script_kwargs)

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="scripts"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 scripts for execution")])
        self.assertEqual(command.stderr.write.call_args_list, [])

        monitor_scripts = [
            {**x, "last_run": None} for x in self.all_monitor_script_dict() if self.assertDatetime(x["last_run"])
        ]
        self.assertEqual(
            monitor_scripts,
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                    "response_text": monitor_scripts[0]["response_text"],
                    "status": "CRITICAL",
                    "status_code": 1,
                }
            ],
        )

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH["post"], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH["request"], apply_slack_requests_request_mock())
    @patch(
        "builtins.open",
        mock_open(
            read_data="\n".join(
                [
                    "from breathecode.utils import ScriptNotification",
                    "raise ScriptNotification('thus spoke kishibe rohan', status='CRITICAL')",
                ]
            )
        ),
    )
    def tests_monitor_with_entity_scripts_in_file_with_critical_error_with_notify(self):
        mock_mailgun = MAILGUN_INSTANCES["post"]
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES["request"]
        mock_slack.call_args_list = []

        application_kwargs = {"notify_email": "pokemon@potato.io"}

        monitor_script_kwargs = {"script_slug": "they-killed-kenny"}

        model = self.generate_models(
            monitor_script=True,
            slack_channel=True,
            credentials_slack=True,
            slack_team=True,
            academy=True,
            application=True,
            application_kwargs=application_kwargs,
            monitor_script_kwargs=monitor_script_kwargs,
        )

        command = Command()
        command.stdout.write = MagicMock()
        command.stderr.write = MagicMock()

        self.assertEqual(command.handle(entity="scripts"), None)
        self.assertEqual(command.stdout.write.call_args_list, [call("Enqueued 1 scripts for execution")])
        self.assertEqual(command.stderr.write.call_args_list, [])

        monitor_scripts = [
            {**x, "last_run": None} for x in self.all_monitor_script_dict() if self.assertDatetime(x["last_run"])
        ]
        self.assertEqual(
            monitor_scripts,
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                    "response_text": monitor_scripts[0]["response_text"],
                    "status": "CRITICAL",
                    "status_code": 1,
                }
            ],
        )

        self.assertEqual(len(mock_mailgun.call_args_list), 1)
        self.assertEqual(len(mock_slack.call_args_list), 1)

from unittest.mock import patch, MagicMock, call
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
)
from ...mixins import MonitoringTestCase
from ....management.commands.monitor import Command

class AcademyCohortTestSuite(MonitoringTestCase):

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH['post'], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH['request'], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH['get'], apply_requests_get_mock([(200, 'https://potato.io', {})]))
    def tests_monitor_without_entity(self):
        mock_mailgun = MAILGUN_INSTANCES['post']
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES['request']
        mock_slack.call_args_list = []

        mock_breathecode = REQUESTS_INSTANCES['get']
        mock_breathecode.call_args_list = []

        command = Command()
        command.stdout.write = MagicMock()

        self.assertEqual(command.handle(), None)
        self.assertEqual(command.stdout.write.call_args_list, [])
        self.assertEqual(self.all_endpoint_dict(), [])

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(mock_breathecode.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH['post'], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH['request'], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH['get'], apply_requests_get_mock([(200, 'https://potato.io', {})]))
    def tests_monitor_with_entity_apps_without_application(self):
        mock_mailgun = MAILGUN_INSTANCES['post']
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES['request']
        mock_slack.call_args_list = []

        mock_breathecode = REQUESTS_INSTANCES['get']
        mock_breathecode.call_args_list = []

        command = Command()
        command.stdout.write = MagicMock()

        self.assertEqual(command.handle(entity='apps'), None)
        self.assertEqual(command.stdout.write.call_args_list, [call('Enqueued 0 apps for diagnostic')])
        self.assertEqual(self.all_endpoint_dict(), [])

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(mock_breathecode.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH['post'], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH['request'], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH['get'], apply_requests_get_mock([(200, 'https://potato.io', {})]))
    def tests_monitor_with_entity_apps_without_endpoints(self):
        mock_mailgun = MAILGUN_INSTANCES['post']
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES['request']
        mock_slack.call_args_list = []

        mock_breathecode = REQUESTS_INSTANCES['get']
        mock_breathecode.call_args_list = []

        model = self.generate_models(application=True)
        command = Command()
        command.stdout.write = MagicMock()

        self.assertEqual(command.handle(entity='apps'), None)
        self.assertEqual(command.stdout.write.call_args_list, [call('Enqueued 1 apps for diagnostic')])
        self.assertEqual(self.all_endpoint_dict(), [])

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(mock_breathecode.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(MAILGUN_PATH['post'], apply_mailgun_requests_post_mock())
    @patch(SLACK_PATH['request'], apply_slack_requests_request_mock())
    @patch(REQUESTS_PATH['get'], apply_requests_get_mock([(200, 'https://potato.io', {})]))
    def tests_monitor_with_entity_apps(self):
        mock_mailgun = MAILGUN_INSTANCES['post']
        mock_mailgun.call_args_list = []

        mock_slack = SLACK_INSTANCES['request']
        mock_slack.call_args_list = []

        mock_breathecode = REQUESTS_INSTANCES['get']
        mock_breathecode.call_args_list = []

        model = self.generate_models(application=True, endpoint=True,
            endpoint_kwargs={'url': 'https://potato.io'})
        command = Command()
        command.stdout.write = MagicMock()

        self.assertEqual(command.handle(entity='apps'), None)
        self.assertEqual(command.stdout.write.call_args_list, [call('Enqueued 1 apps for diagnostic')])

        endpoints = [{**endpoint, 'last_check': None} for endpoint in
            self.all_endpoint_dict() if self.assertDatetime(endpoint['last_check'])]
        self.assertEqual(endpoints, [{
            **self.model_to_dict(model, 'endpoint'),
            'frequency_in_minutes': 30.0,
            'severity_level': 5,
            'status_text': 'Status withing the 2xx range',
        }])

        self.assertEqual(mock_mailgun.call_args_list, [])
        self.assertEqual(mock_slack.call_args_list, [])
        self.assertEqual(mock_breathecode.call_args_list, [call(
            'https://potato.io',
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
            },
            timeout=2
        )])





        # dicts = self.all_answer_dict()
        # self.check_email_contain_a_correct_token('es', dicts, mock_mailgun, model)
        # self.check_slack_contain_a_correct_token('es', dicts, mock_slack, model)

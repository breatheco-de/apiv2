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
    apply_logging_logger_mock
)
from ..mixins import MonitoringTestCase
from breathecode.monitoring.actions import run_script


class AcademyCohortTestSuite(MonitoringTestCase):
    """
    🔽🔽🔽 With bad entity 🔽🔽🔽
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_send_survey_no_reminder(self):

        monitor_script_kwargs = {"script_slug": "send_survey_reminder"}

        model = self.generate_models(monitor_script=True,
                                     monitor_script_kwargs=monitor_script_kwargs)

        script = run_script(model.monitor_script)

        del script['slack_payload']

        expected = {
            "severity_level": 5,
            "status": 'OPERATIONAL',
            "details": '{\n'
            '    "severity_level": 5,\n'
            '    "details": "No reminders\\n",\n'
            '    "status": "OPERATIONAL"\n'
            '}',
            "text": '{\n'
                    '    "severity_level": 5,\n'
                    '    "details": "No reminders\\n",\n'
                    '    "status": "OPERATIONAL"\n'
                    '}'
        }

        self.assertEqual(script, expected)

        self.assertEqual(self.all_monitor_script_dict(), [{
            **self.model_to_dict(model, 'monitor_script'),
        }])

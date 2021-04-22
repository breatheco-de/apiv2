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
from breathecode.admissions.models import Cohort, Academy


class AcademyCohortTestSuite(MonitoringTestCase):
    """
    🔽🔽🔽 With bad entity 🔽🔽🔽
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_user_status_postponed_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"}

        model = self.generate_models(cohort_user=True, cohort=True, academy=True, monitor_script=True,
                                     monitor_script_kwargs=monitor_script_kwargs,
                                     cohort_user_kwargs={
                                         'educational_status': "POSTPONED"},
                                     cohort_kwargs={'stage': "ENDED"}
                                     )

        script = run_script(model.monitor_script)

        del script['slack_payload']
        del script['text']

        expected = {
                    'severity_level': 5,
                    'status': 'OPERATIONAL',
                    }

        self.assertEqual(script, expected)

        self.assertEqual(self.all_monitor_script_dict(), [{
            **self.model_to_dict(model, 'monitor_script'),
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_user_status_suspended_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"}

        model = self.generate_models(cohort_user=True, cohort=True, academy=True, monitor_script=True,
                                     monitor_script_kwargs=monitor_script_kwargs,
                                     cohort_user_kwargs={
                                         'educational_status': "SUSPENDED"},
                                     cohort_kwargs={'stage': "ENDED"}
                                     )

        script = run_script(model.monitor_script)

        del script['slack_payload']
        del script['text']

        expected = {
                    'severity_level': 5,
                    'status': script['status'],
                    }

        self.assertEqual(script, expected)

        self.assertEqual(self.all_monitor_script_dict(), [{
            **self.model_to_dict(model, 'monitor_script'),
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_user_status_graduated_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"}

        model = self.generate_models(cohort_user=True, cohort=True, academy=True, monitor_script=True,
                                     monitor_script_kwargs=monitor_script_kwargs,
                                     cohort_user_kwargs={
                                         'educational_status': "GRADUATED"},
                                     cohort_kwargs={'stage': "ENDED"}
                                     )

        script = run_script(model.monitor_script)

        del script['slack_payload']
        del script['text']

        expected = {
                    'severity_level': 5,
                    'status': 'OPERATIONAL',
                    }

        self.assertEqual(script, expected)

        self.assertEqual(self.all_monitor_script_dict(), [{
            **self.model_to_dict(model, 'monitor_script'),
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_user_status_dropped_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"}

        model = self.generate_models(cohort_user=True, cohort=True, academy=True, monitor_script=True,
                                     monitor_script_kwargs=monitor_script_kwargs,
                                     cohort_user_kwargs={
                                         'educational_status': "DROPPED"},
                                     cohort_kwargs={'stage': "ENDED"}
                                     )

        script = run_script(model.monitor_script)

        del script['slack_payload']
        del script['text']

        expected = {
                    'severity_level': 5,
                    'status': 'OPERATIONAL',
                    }

        self.assertEqual(script, expected)

        self.assertEqual(self.all_monitor_script_dict(), [{
            **self.model_to_dict(model, 'monitor_script'),
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_user_status_active_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"}

        model = self.generate_models(cohort_user=True, cohort=True, academy=True, monitor_script=True,
                                     monitor_script_kwargs=monitor_script_kwargs,
                                     cohort_user_kwargs={
                                         'educational_status': "ACTIVE"},
                                     cohort_kwargs={'stage': "ENDED"}
                                     )

        script = run_script(model.monitor_script)

        del script['slack_payload']
        del script['text']

        expected = {
                    'severity_level': 5,
                    'status': 'MINOR',
                    'error_slug': None,
                    }

        self.assertEqual(script, expected)

        self.assertEqual(self.all_monitor_script_dict(), [{
            **self.model_to_dict(model, 'monitor_script'),
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_user_status_active_non_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"}

        model = self.generate_models(cohort_user=True, cohort=True, academy=True, monitor_script=True,
                                     monitor_script_kwargs=monitor_script_kwargs,
                                     cohort_user_kwargs={
                                         'educational_status': "ACTIVE"},
                                     cohort_kwargs={'stage': "FINAL_PROJECT"}
                                     )

        script = run_script(model.monitor_script)

        del script['slack_payload']
        del script['text']

        expected = {
                    'severity_level': 5,
                    'status': 'OPERATIONAL',
                    }

        self.assertEqual(script, expected)

        self.assertEqual(self.all_monitor_script_dict(), [{
            **self.model_to_dict(model, 'monitor_script'),
        }])

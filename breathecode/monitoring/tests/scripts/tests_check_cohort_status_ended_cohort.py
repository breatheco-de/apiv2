from datetime import timedelta
from unittest.mock import MagicMock, call, mock_open, patch

from django.utils import timezone

from breathecode.admissions.models import Academy, Cohort
from breathecode.monitoring.actions import run_script
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    LOGGING_INSTANCES,
    LOGGING_PATH,
    MAILGUN_INSTANCES,
    MAILGUN_PATH,
    REQUESTS_INSTANCES,
    REQUESTS_PATH,
    SLACK_INSTANCES,
    SLACK_PATH,
    apply_google_cloud_blob_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_client_mock,
    apply_logging_logger_mock,
    apply_mailgun_requests_post_mock,
    apply_requests_get_mock,
    apply_slack_requests_request_mock,
)

from ..mixins import MonitoringTestCase


class AcademyCohortTestSuite(MonitoringTestCase):
    """
    🔽🔽🔽 Check for cohort.stage == 'ENDED'
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def tests_check_cohort__status_ended_date_greater_than_now(self):

        monitor_script_kwargs = {"script_slug": "check_cohort_status_ended_cohort"}
        ending_date = timezone.now() + timedelta(weeks=2)
        model = self.generate_models(
            cohort=True,
            academy=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_kwargs={"ending_date": ending_date},
        )

        script = run_script(model.monitor_script)

        del script["slack_payload"]
        del script["text"]
        del script["title"]

        expected = {
            "severity_level": 5,
            "status": "OPERATIONAL",
        }

        self.assertEqual(script, expected)

        self.assertEqual(self.all_monitor_script_dict(), [{**self.model_to_dict(model, "monitor_script")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def tests_check_cohort__ending_date_passed_with_status_ended(self):

        monitor_script_kwargs = {"script_slug": "check_cohort_status_ended_cohort"}
        ending_date = timezone.now() - timedelta(weeks=2)
        model = self.generate_models(
            cohort=True,
            academy=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_kwargs={"ending_date": ending_date, "stage": "ENDED"},
        )

        script = run_script(model.monitor_script)

        del script["slack_payload"]
        del script["text"]
        del script["title"]

        expected = {"severity_level": 5, "status": "OPERATIONAL"}

        self.assertEqual(script, expected)

        self.assertEqual(
            self.all_monitor_script_dict(),
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                }
            ],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def tests_check_cohort__ending_date_passed_with_status_final_project(self):

        monitor_script_kwargs = {"script_slug": "check_cohort_status_ended_cohort"}
        ending_date = timezone.now() - timedelta(weeks=2)
        model = self.generate_models(
            cohort=True,
            academy=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_kwargs={"ending_date": ending_date, "stage": "FINAL_PROJECT"},
        )

        script = run_script(model.monitor_script)

        del script["slack_payload"]
        del script["text"]
        del script["title"]

        expected = {
            "btn": None,
            "severity_level": 100,
            "status": "CRITICAL",
            "error_slug": "cohort-stage-should-be-ended",
        }

        self.assertEqual(script, expected)

        self.assertEqual(
            self.all_monitor_script_dict(),
            [
                {
                    **self.model_to_dict(model, "monitor_script"),
                }
            ],
        )

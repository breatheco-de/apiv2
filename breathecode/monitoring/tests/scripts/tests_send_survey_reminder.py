from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import MonitoringTestCase
from breathecode.monitoring.actions import run_script


class AcademyCohortTestSuite(MonitoringTestCase):
    """
    🔽🔽🔽 With bad entity 🔽🔽🔽
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def tests_send_survey__reminder_no_survey(self):

        monitor_script_kwargs = {"script_slug": "send_survey_reminder"}

        model = self.generate_models(
            academy=True, skip_cohort=True, monitor_script=True, monitor_script_kwargs=monitor_script_kwargs
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
    def tests_send_survey__ending_date_less_than_now(self):

        monitor_script_kwargs = {"script_slug": "send_survey_reminder"}
        ending_date = timezone.now() - timedelta(weeks=1)
        sent_at = timezone.now() - timedelta(weeks=5)
        model = self.generate_models(
            cohort=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_kwargs={"ending_date": ending_date},
            survey=True,
            survey_kwargs={"sent_at": sent_at},
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
    def tests_send_survey__kickoff_date_greater_than_now(self):

        monitor_script_kwargs = {"script_slug": "send_survey_reminder"}
        kickoff_date = timezone.now() + timedelta(weeks=1)
        sent_at = timezone.now() - timedelta(weeks=5)
        model = self.generate_models(
            cohort=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_kwargs={"kickoff_date": kickoff_date},
            survey=True,
            survey_kwargs={"sent_at": sent_at},
        )

        script = run_script(model.monitor_script)

        del script["slack_payload"]
        del script["text"]
        del script["title"]

        expected = {"severity_level": 5, "status": "OPERATIONAL"}
        self.assertEqual(script, expected)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def tests_send_survey__latest_survey_less_four_weeks(self):

        monitor_script_kwargs = {"script_slug": "send_survey_reminder"}
        ending_date = timezone.now() + timedelta(weeks=4)
        kickoff_date = timezone.now() - timedelta(weeks=12)

        base = self.generate_models(
            academy=True,
            cohort=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_kwargs={"ending_date": ending_date, "kickoff_date": kickoff_date},
        )
        sent_at = timezone.now() - timedelta(weeks=1)
        models = [
            self.generate_models(survey=True, survey_kwargs={"sent_at": sent_at}, models=base) for _ in range(0, 2)
        ]

        script = run_script(models[1].monitor_script)

        del script["slack_payload"]
        del script["text"]
        del script["title"]

        expected = {
            "severity_level": 5,
            "status": "OPERATIONAL",
        }
        self.assertEqual(script, expected)

    """
    🔽🔽🔽 Cohort have pending surveys to send
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def tests_send_survey__latest_survey_greater_four_weeks(self):

        monitor_script_kwargs = {"script_slug": "send_survey_reminder"}
        ending_date = timezone.now() + timedelta(days=2)
        kickoff_date = timezone.now() - timedelta(weeks=8)

        base = self.generate_models(
            academy=True,
            cohort=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_kwargs={
                "ending_date": ending_date,
                "kickoff_date": kickoff_date,
                "stage": "STARTED",
            },
        )

        sent_at = timezone.now() - timedelta(weeks=6)

        models = [
            self.generate_models(survey=True, survey_kwargs={"status": "SENT", "sent_at": sent_at}, models=base)
            for _ in range(0, 2)
        ]

        script = run_script(models[1].monitor_script)

        del script["slack_payload"]
        del script["text"]
        del script["title"]

        expected = {
            "btn": None,
            "severity_level": 5,
            "error_slug": "cohort-have-pending-surveys",
            "status": "MINOR",
        }

        self.assertEqual(script, expected)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def tests_send_survey__latest_survey_greater_four_weeks__two_cohorts__two_survey(self):

        monitor_script_kwargs = {"script_slug": "send_survey_reminder"}
        ending_date = timezone.now() + timedelta(days=2)
        kickoff_date = timezone.now() - timedelta(days=12)

        base = self.generate_models(
            academy=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            skip_cohort=True,
        )

        sent_at = timezone.now() - timedelta(weeks=6)

        models = [
            self.generate_models(
                survey=True,
                cohort=True,
                survey_kwargs={"status": "SENT", "sent_at": sent_at},
                models=base,
                cohort_kwargs={
                    "ending_date": ending_date,
                    "kickoff_date": kickoff_date,
                    "stage": "FINAL_PROJECT",
                },
            )
            for _ in range(0, 2)
        ]

        script = run_script(models[1].monitor_script)
        del script["slack_payload"]
        del script["text"]
        del script["title"]

        expected = {
            "btn": None,
            "severity_level": 5,
            "error_slug": "cohort-have-pending-surveys",
            "status": "MINOR",
        }

        self.assertEqual(script, expected)

    """
    🔽🔽🔽 Cohort that never ends
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def tests_send_survey__latest_survey_greater_four_weeks__cohort_never_ends(self):

        monitor_script_kwargs = {"script_slug": "send_survey_reminder"}
        ending_date = timezone.now() + timedelta(days=2)
        kickoff_date = timezone.now() - timedelta(days=2)

        base = self.generate_models(
            academy=True,
            cohort=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_kwargs={
                # 'ending_date': ending_date,
                "kickoff_date": kickoff_date,
                "never_ends": True,
            },
        )

        sent_at = timezone.now() - timedelta(weeks=6)

        models = [
            self.generate_models(survey=True, survey_kwargs={"sent_at": sent_at}, models=base) for _ in range(0, 2)
        ]

        script = run_script(models[1].monitor_script)

        del script["slack_payload"]
        del script["text"]
        del script["title"]

        expected = {
            "severity_level": 5,
            "status": "OPERATIONAL",
        }

        self.assertEqual(script, expected)

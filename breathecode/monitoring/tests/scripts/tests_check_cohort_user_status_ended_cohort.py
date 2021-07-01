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
    🔽🔽🔽 Bad educational status
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_user_status__postponed_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"
        }

        model = self.generate_models(
            cohort_user=True,
            cohort=True,
            academy=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_user_kwargs={'educational_status': "POSTPONED"},
            cohort_kwargs={'stage': "ENDED"})

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
    def tests_check_user_status__suspended_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"
        }

        model = self.generate_models(
            cohort_user=True,
            cohort=True,
            academy=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_user_kwargs={'educational_status': "SUSPENDED"},
            cohort_kwargs={'stage': "ENDED"})

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
    def tests_check_user_status__graduated_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"
        }

        model = self.generate_models(
            cohort_user=True,
            cohort=True,
            academy=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_user_kwargs={'educational_status': "GRADUATED"},
            cohort_kwargs={'stage': "ENDED"})

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
    def tests_check_user_status__dropped_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"
        }

        model = self.generate_models(
            cohort_user=True,
            cohort=True,
            academy=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_user_kwargs={'educational_status': "DROPPED"},
            cohort_kwargs={'stage': "ENDED"})

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

    """
    🔽🔽🔽 Active student in one ended cohort
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_user_status__active_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"
        }

        model = self.generate_models(
            cohort_user=True,
            cohort=True,
            academy=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_user_kwargs={'educational_status': "ACTIVE"},
            cohort_kwargs={'stage': "ENDED"})

        script = run_script(model.monitor_script)

        del script['slack_payload']
        del script['text']

        expected = {
            'severity_level': 5,
            'status': 'MINOR',
            'error_slug': 'ended-cohort-had-active-users',
        }

        self.assertEqual(script, expected)
        self.assertEqual(self.all_monitor_script_dict(), [{
            **self.model_to_dict(model, 'monitor_script'),
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_user_status__active_non_ended_cohort(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"
        }

        model = self.generate_models(
            cohort_user=True,
            cohort=True,
            academy=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_user_kwargs={'educational_status': "ACTIVE"},
            cohort_kwargs={'stage': "FINAL_PROJECT"})

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

    """
    🔽🔽🔽 Active student in one never ends cohort
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_user_status__cohort_never_ends(self):

        monitor_script_kwargs = {
            "script_slug": "check_cohort_user_status_ended_cohort"
        }

        model = self.generate_models(
            cohort_user=True,
            cohort=True,
            academy=True,
            monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs,
            cohort_user_kwargs={'educational_status': "ACTIVE"},
            cohort_kwargs={
                'stage': "ENDED",
                'never_ends': True
            })

        script = run_script(model.monitor_script)

        del script['slack_payload']
        del script['text']

        expected = {'severity_level': 5, 'status': 'OPERATIONAL'}

        self.assertEqual(script, expected)
        self.assertEqual(self.all_monitor_script_dict(), [{
            **self.model_to_dict(model, 'monitor_script'),
        }])

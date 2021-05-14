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
    🔽🔽🔽 Without data
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_certificates_without_timeslots__without_data(self):
        monitor_script_kwargs = {
            "script_slug": "check_certificates_without_timeslots",
        }

        model = self.generate_models(academy=True, monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs)

        script = run_script(model.monitor_script)
        del script['slack_payload']

        expected = {
            'severity_level': 5,
            'status': 'OPERATIONAL',
            'text': 'Done!\n',
        }

        self.assertEqual(script, expected)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Certificate without timeslots
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_certificates_without_timeslots__one_certificate_without_timeslots(self):
        monitor_script_kwargs = {
            "script_slug": "check_certificates_without_timeslots",
        }

        model = self.generate_models(academy=True, monitor_script=True, academy_certificate=True,
                monitor_script_kwargs=monitor_script_kwargs)

        script = run_script(model.monitor_script)
        del script['slack_payload']
        del script['text']

        expected = {
            'severity_level': 5,
            'status': 'MINOR',
            'error_slug': 'certificates-without-timeslots',
        }

        self.assertEqual(script, expected)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_certificates_without_timeslots__two_certificate_without_timeslots(self):
        monitor_script_kwargs = {
            "script_slug": "check_certificates_without_timeslots",
        }

        base = self.generate_models(academy=True, monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs)

        models = [self.generate_models(academy_certificate=True, models=base) for _ in range(0, 2)]

        script = run_script(models[0].monitor_script)
        del script['slack_payload']
        del script['text']

        expected = {
            'severity_level': 5,
            'status': 'MINOR',
            'error_slug': 'certificates-without-timeslots',
        }

        self.assertEqual(script, expected)
        self.assertEqual(self.all_certificate_time_slot_dict(), [])

    """
    🔽🔽🔽 Certificate with timeslot
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_certificates_without_timeslots__one_certificate_with_certificate_timeslots__with_cohort(self):
        monitor_script_kwargs = {
            "script_slug": "check_certificates_without_timeslots",
        }

        model = self.generate_models(academy=True, monitor_script=True, academy_certificate=True,
                monitor_script_kwargs=monitor_script_kwargs, certificate_time_slot=True,
                cohort=True, syllabus=True)

        script = run_script(model.monitor_script)
        del script['slack_payload']
        del script['text']

        expected = {
            'severity_level': 5,
            'status': 'OPERATIONAL',
        }

        self.assertEqual(script, expected)
        self.assertEqual(self.all_certificate_time_slot_dict(), [{
            **self.model_to_dict(model, 'certificate_time_slot'),
        }])

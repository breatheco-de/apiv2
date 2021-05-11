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

    # """
    # 🔽🔽🔽 Without data
    # """
    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def tests_check_certificates_without_timeslots__without_data____(self):
    #     monitor_script_kwargs = {
    #         "script_slug": "check_certificates_without_timeslots",
    #     }

    #     models = [
    #         self.generate_models(academy=True, monitor_script=True,
    #             monitor_script_kwargs=monitor_script_kwargs),
    #         self.generate_models(academy=True, academy_certificate=True)
    #     ]

    #     script = run_script(models[0].monitor_script)
    #     del script['slack_payload']

    #     expected = {
    #         'severity_level': 5,
    #         'status': 'OPERATIONAL',
    #         'text': 'Done!\n',
    #     }

    #     self.assertEqual(script, expected)
    #     self.assertEqual(self.all_cohort_time_slot_dict(), [])

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
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    """
    🔽🔽🔽 Certificate with timeslot
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_certificates_without_timeslots__one_certificate_with_certificate_timeslots__without_cohort(self):
        monitor_script_kwargs = {
            "script_slug": "check_certificates_without_timeslots",
        }

        model = self.generate_models(academy=True, monitor_script=True, academy_certificate=True,
                monitor_script_kwargs=monitor_script_kwargs, certificate_time_slot=True)

        script = run_script(model.monitor_script)
        del script['slack_payload']
        del script['text']

        expected = {
            'severity_level': 5,
            'status': 'OPERATIONAL',
        }

        self.assertEqual(script, expected)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

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
        self.assertEqual(self.all_cohort_time_slot_dict(), [{
            'id': 1,
            'cohort_id': 1,
            'parent_id': 1,
            'starting_at': model.certificate_time_slot.starting_at,
            'ending_at': model.certificate_time_slot.ending_at,
            'recurrent': model.certificate_time_slot.recurrent,
            'recurrency_type': model.certificate_time_slot.recurrency_type,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_certificates_without_timeslots__one_certificate_with_two_certificate_timeslots__with_cohort(self):
        monitor_script_kwargs = {
            "script_slug": "check_certificates_without_timeslots",
        }

        base = self.generate_models(academy=True, monitor_script=True,
            academy_certificate=True,
            monitor_script_kwargs=monitor_script_kwargs)

        models = [self.generate_models(cohort=True, syllabus=True, certificate_time_slot=True,
            models=base) for _ in range(0, 2)]

        # model = self.generate_models(academy=True, monitor_script=True, academy_certificate=True,
        #         monitor_script_kwargs=monitor_script_kwargs, certificate_time_slot=True,
        #         cohort=True, syllabus=True)

        script = run_script(models[0].monitor_script)
        del script['slack_payload']
        del script['text']

        expected = {
            'severity_level': 5,
            'status': 'OPERATIONAL',
        }

        self.assertEqual(script, expected)

        model1 = models[0]
        model2 = models[1]

        self.assertEqual(script, expected)
        self.assertEqual(self.all_cohort_time_slot_dict(), [{
            'id': 1,
            'cohort_id': 1,
            'parent_id': 1,
            'starting_at': model1.certificate_time_slot.starting_at,
            'ending_at': model1.certificate_time_slot.ending_at,
            'recurrent': model1.certificate_time_slot.recurrent,
            'recurrency_type': model1.certificate_time_slot.recurrency_type,
        }, {
            'id': 2,
            'cohort_id': 2,
            'parent_id': 1,
            'starting_at': model1.certificate_time_slot.starting_at,
            'ending_at': model1.certificate_time_slot.ending_at,
            'recurrent': model1.certificate_time_slot.recurrent,
            'recurrency_type': model1.certificate_time_slot.recurrency_type,
        }, {
            'id': 3,
            'cohort_id': 1,
            'parent_id': 2,
            'starting_at': model2.certificate_time_slot.starting_at,
            'ending_at': model2.certificate_time_slot.ending_at,
            'recurrent': model2.certificate_time_slot.recurrent,
            'recurrency_type': model2.certificate_time_slot.recurrency_type,
        }, {
            'id': 4,
            'cohort_id': 2,
            'parent_id': 2,
            'starting_at': model2.certificate_time_slot.starting_at,
            'ending_at': model2.certificate_time_slot.ending_at,
            'recurrent': model2.certificate_time_slot.recurrent,
            'recurrency_type': model2.certificate_time_slot.recurrency_type,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_certificates_without_timeslots__two_certificate_with_certificate_timeslots__with_cohort(self):
        monitor_script_kwargs = {
            "script_slug": "check_certificates_without_timeslots",
        }

        base = self.generate_models(academy=True, monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs)

        models = [self.generate_models(academy_certificate=True, certificate_time_slot=True,
            cohort_time_slot=True, cohort=True, syllabus=True, models=base)
            for _ in range(0, 2)]

        script = run_script(models[0].monitor_script)
        del script['slack_payload']
        del script['text']

        expected = {
            'severity_level': 5,
            'status': 'OPERATIONAL',
        }

        self.assertEqual(script, expected)
        self.assertEqual(self.all_cohort_time_slot_dict(), [{
            'id': model.certificate_time_slot.id,
            'cohort_id': model.certificate_time_slot.id,
            'parent_id': model.certificate_time_slot.id,
            'starting_at': model.certificate_time_slot.starting_at,
            'ending_at': model.certificate_time_slot.ending_at,
            'recurrent': model.certificate_time_slot.recurrent,
            'recurrency_type': model.certificate_time_slot.recurrency_type,
        } for model in models])

    """
    🔽🔽🔽 Certificate with timeslot it's updated cohort timeslots
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_certificates_without_timeslots__two_certificate_with_certificate_timeslots__with_cohort_timeslot(self):
        monitor_script_kwargs = {
            "script_slug": "check_certificates_without_timeslots",
        }

        model = self.generate_models(academy=True, monitor_script=True, academy_certificate=True,
                monitor_script_kwargs=monitor_script_kwargs, certificate_time_slot=True,
                cohort=True, syllabus=True, cohort_time_slot=True)

        script = run_script(model.monitor_script)
        del script['slack_payload']
        del script['text']

        expected = {
            'severity_level': 5,
            'status': 'OPERATIONAL',
        }

        self.assertEqual(script, expected)
        self.assertEqual(self.all_cohort_time_slot_dict(), [{
            'id': 1,
            'cohort_id': 1,
            'parent_id': 1,
            'starting_at': model.certificate_time_slot.starting_at,
            'ending_at': model.certificate_time_slot.ending_at,
            'recurrent': model.certificate_time_slot.recurrent,
            'recurrency_type': model.certificate_time_slot.recurrency_type,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_certificates_without_timeslots__one_certificate_with_two_certificate_timeslots__with_cohort_timeslot(self):
        monitor_script_kwargs = {
            "script_slug": "check_certificates_without_timeslots",
        }

        base = self.generate_models(academy=True, monitor_script=True,
            academy_certificate=True,
            monitor_script_kwargs=monitor_script_kwargs)

        models = [self.generate_models(cohort=True, syllabus=True, certificate_time_slot=True,
            cohort_time_slot=True, models=base) for _ in range(0, 2)]

        script = run_script(models[0].monitor_script)
        del script['slack_payload']
        del script['text']

        expected = {
            'severity_level': 5,
            'status': 'OPERATIONAL',
        }

        model1 = models[0]
        model2 = models[1]

        self.assertEqual(script, expected)
        self.assertEqual(self.all_cohort_time_slot_dict(), [{
            'id': 1,
            'cohort_id': 1,
            'parent_id': 1,
            'starting_at': model1.certificate_time_slot.starting_at,
            'ending_at': model1.certificate_time_slot.ending_at,
            'recurrent': model1.certificate_time_slot.recurrent,
            'recurrency_type': model1.certificate_time_slot.recurrency_type,
        }, {
            'id': 2,
            'cohort_id': 2,
            'parent_id': 2,
            'starting_at': model2.certificate_time_slot.starting_at,
            'ending_at': model2.certificate_time_slot.ending_at,
            'recurrent': model2.certificate_time_slot.recurrent,
            'recurrency_type': model2.certificate_time_slot.recurrency_type,
        }, {
            'id': 3,
            'cohort_id': 2,
            'parent_id': 1,
            'starting_at': model1.certificate_time_slot.starting_at,
            'ending_at': model1.certificate_time_slot.ending_at,
            'recurrent': model1.certificate_time_slot.recurrent,
            'recurrency_type': model1.certificate_time_slot.recurrency_type,
        }, {
            'id': 4,
            'cohort_id': 1,
            'parent_id': 2,
            'starting_at': model2.certificate_time_slot.starting_at,
            'ending_at': model2.certificate_time_slot.ending_at,
            'recurrent': model2.certificate_time_slot.recurrent,
            'recurrency_type': model2.certificate_time_slot.recurrency_type,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def tests_check_certificates_without_timeslots__two_certificate_with_certificate_timeslots__with_cohort_timeslot(self):
        monitor_script_kwargs = {
            "script_slug": "check_certificates_without_timeslots",
        }

        base = self.generate_models(academy=True, monitor_script=True,
            monitor_script_kwargs=monitor_script_kwargs)

        models = [self.generate_models(academy_certificate=True, certificate_time_slot=True,
            cohort=True, syllabus=True, cohort_time_slot=True, models=base) for _ in range(0, 2)]

        script = run_script(models[0].monitor_script)
        del script['slack_payload']
        del script['text']

        expected = {
            'severity_level': 5,
            'status': 'OPERATIONAL',
        }

        self.assertEqual(script, expected)
        self.assertEqual(self.all_cohort_time_slot_dict(), [{
            'id': model.certificate_time_slot.id,
            'cohort_id': model.certificate_time_slot.id,
            'parent_id': model.certificate_time_slot.id,
            'starting_at': model.certificate_time_slot.starting_at,
            'ending_at': model.certificate_time_slot.ending_at,
            'recurrent': model.certificate_time_slot.recurrent,
            'recurrency_type': model.certificate_time_slot.recurrency_type,
        } for model in models])
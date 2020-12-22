"""
Admin tests
"""
from breathecode.admissions.models import UP_TO_DATE
from unittest.mock import patch, call

from django.http.request import HttpRequest
from breathecode.tests.mocks import (
    DJANGO_CONTRIB_PATH,
    DJANGO_CONTRIB_INSTANCES,
    apply_django_contrib_messages_mock,
)
from ...admin import cohort_bulk_certificate
from ...models import Certificate, Cohort
from ..mixins import CertificateTestCase
from ..mocks import (
    ACTIONS_PATH,
    ACTIONS_INSTANCES,
    apply_generate_certificate_mock,
)

class AdminCohortBulkCertificateTestCase(CertificateTestCase):
    """Tests action cohort_bulk_certificate"""
    # @patch(ACTIONS_PATH['certificate_screenshot'], apply_certificate_screenshot_mock())
    @patch(ACTIONS_PATH['generate_certificate'], apply_generate_certificate_mock())
    # @patch(ACTIONS_PATH['remove_certificate_screenshot'], apply_remove_certificate_screenshot_mock())
    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_cohort_bulk_certificate_without_cohort(self):
        """cohort_bulk_certificate don't call open in development environment"""
        request = HttpRequest()
        mock = DJANGO_CONTRIB_INSTANCES['messages']
        mock.success.call_args_list = []
        mock.error.call_args_list = []

        # model = self.generate_models()

        self.assertEqual(cohort_bulk_certificate(None, request, Cohort.objects.filter()), None)

        self.assertEqual(mock.success.call_args_list, [call(request, message='Scheduled certificate'
            ' generation')])
        self.assertEqual(mock.error.call_args_list, [])

        self.assertEqual(self.count_cohort(), 0)
        self.assertEqual(self.count_certificate(), 0)

    # @patch(ACTIONS_PATH['certificate_screenshot'], apply_certificate_screenshot_mock())
    @patch(ACTIONS_PATH['generate_certificate'], apply_generate_certificate_mock())
    # @patch(ACTIONS_PATH['remove_certificate_screenshot'], apply_remove_certificate_screenshot_mock())
    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_cohort_bulk_certificate_with_cohort(self):
        """cohort_bulk_certificate don't call open in development environment"""
        request = HttpRequest()
        mock = DJANGO_CONTRIB_INSTANCES['messages']
        mock.success.call_args_list = []
        mock.error.call_args_list = []

        model = self.generate_models(cohort=True)
        db_cohort = self.model_to_dict(model, 'cohort')
        db_certificate = self.model_to_dict(model, 'certificate')

        self.assertEqual(self.count_certificate(), 1)
        self.assertEqual(cohort_bulk_certificate(None, request, Cohort.objects.filter()), None)

        self.assertEqual(mock.success.call_args_list, [call(request, message='Scheduled certificate'
            ' generation')])
        self.assertEqual(mock.error.call_args_list, [])

        self.assertEqual(self.all_cohort_dict(), [db_cohort])
        self.assertEqual(self.all_certificate_dict(), [db_certificate])

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_cohort_bulk_certificate_with_cohort_with_required_models_but_bad_status(self):
        """cohort_bulk_certificate don't call open in development environment"""
        request = HttpRequest()
        mock = DJANGO_CONTRIB_INSTANCES['messages']
        mock.success.call_args_list = []
        mock.error.call_args_list = []

        models = [self.generate_models('en', specialty=True, finished=True,
            layout_design=True, teacher=True, stage=True, cohort_user=True, certificate=True)]

        params = models.copy()[0]
        del params['user']
        del params['cohort_user']
        
        models = models + [self.generate_models('en', cohort_user=True, models=params) for _ in
            range(0, 2)]

        self.assertEqual(self.count_user_specialty(), 0)
        self.assertEqual(self.count_certificate(), 1)
        self.assertEqual(cohort_bulk_certificate(None, request, Cohort.objects.filter()), None)

        db_cohort = [self.model_to_dict(models[0], 'cohort')]
        db_certificate = [self.model_to_dict(models[0], 'certificate')]

        for _ in range(0, 3):

            self.assertEqual(mock.success.call_args_list, [call(request, message='Scheduled certificate'
                ' generation')])
            self.assertEqual(mock.error.call_args_list, [])

        self.assertEqual(self.check_all_token(self.all_user_specialty_dict()), [])

        self.assertEqual(self.all_cohort_dict(), db_cohort)
        self.assertEqual(self.all_certificate_dict(), db_certificate)

    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_cohort_bulk_certificate_with_cohort_with_required_models(self):
        """cohort_bulk_certificate don't call open in development environment"""
        request = HttpRequest()
        mock = DJANGO_CONTRIB_INSTANCES['messages']
        mock.success.call_args_list = []
        mock.error.call_args_list = []

        models = [self.generate_models('en', finantial_status=UP_TO_DATE, specialty=True, finished=True,
            layout_design=True, teacher=True, stage=True, cohort_user=True, certificate=True)]

        params = models.copy()[0]
        del params['user']
        del params['cohort_user']
        
        models = models + [self.generate_models('en', finantial_status=UP_TO_DATE, cohort_user=True,
            models=params) for _ in range(0, 2)]

        self.assertEqual(self.count_user_specialty(), 0)
        self.assertEqual(self.count_certificate(), 1)
        self.assertEqual(cohort_bulk_certificate(None, request, Cohort.objects.filter()), None)

        db_cohort = [self.model_to_dict(models[0], 'cohort')]
        db_certificate = [self.model_to_dict(models[0], 'certificate')]

        for _ in range(0, 3):

            self.assertEqual(mock.success.call_args_list, [call(request, message='Scheduled certificate'
                ' generation')])
            self.assertEqual(mock.error.call_args_list, [])

        first_name = models[0]['teacher_user'].first_name
        last_name = models[0]['teacher_user'].last_name

        expected = [{
            'id': id,
            'user_id': 1 if id == 1 else id + 1,
            'specialty_id': 1,
            'expires_at': None,
            'academy_id': 1,
            'layout_id': 1,
            'cohort_id': 1,
            'signed_by': f'{first_name} {last_name}',
            'signed_by_role': 'Main Instructor',
            'preview_url': None,
        } for id in range(1, 4)]

        self.assertEqual(self.check_all_token(self.all_user_specialty_dict()), expected)

        self.assertEqual(self.all_cohort_dict(), db_cohort)
        self.assertEqual(self.all_certificate_dict(), db_certificate)

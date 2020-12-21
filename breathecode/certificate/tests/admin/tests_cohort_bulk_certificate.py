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

    # @patch(ACTIONS_PATH['certificate_screenshot'], apply_certificate_screenshot_mock())
    # @patch(ACTIONS_PATH['generate_certificate'], apply_generate_certificate_mock())
    # @patch(ACTIONS_PATH['remove_certificate_screenshot'], apply_remove_certificate_screenshot_mock())
    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    def test_cohort_bulk_certificate_with_cohort_with_required_models(self):
        """cohort_bulk_certificate don't call open in development environment"""
        request = HttpRequest()
        mock = DJANGO_CONTRIB_INSTANCES['messages']
        mock.success.call_args_list = []
        mock.error.call_args_list = []

        models = [self.generate_models('en', finantial_status=UP_TO_DATE, specialty=True, finished=True,
            layout_design=True, teacher=True, stage=True, cohort_user=True, certificate=True)]
        
        models = models + [self.generate_models('en', finantial_status=UP_TO_DATE, specialty=True,
            finished=True, teacher=True, stage=True, cohort_user=True, certificate=True) for _ in
            range(0, 2)]

        db_cohort = []
        db_certificate = []

        self.assertEqual(self.count_user_specialty(), 0)
        self.assertEqual(self.count_certificate(), 3)
        self.assertEqual(cohort_bulk_certificate(None, request, Cohort.objects.filter()), None)

        for model in models:
            db_cohort = db_cohort + [self.model_to_dict(model, 'cohort')]
            db_certificate = db_certificate + [self.model_to_dict(model, 'certificate')]

            self.assertEqual(mock.success.call_args_list, [call(request, message='Scheduled certificate'
                ' generation')])
            self.assertEqual(mock.error.call_args_list, [])

        self.assertEqual(self.count_user_specialty(), 3)
        self.assertEqual(self.all_cohort_dict(), db_cohort)
        self.assertEqual(self.all_certificate_dict(), db_certificate)

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # @patch(CELERY_PATH['shared_task'], apply_celery_shared_task_mock())
    # def test_generate_certificate_lang_es(self):
    #     """generate_certificate"""
    #     model = self.generate_models('es', finantial_status=UP_TO_DATE, specialty=True, finished=True,
    #         layout_design=True, teacher=True, stage=True, cohort_user=True, certificate=True)
    #     certificate = generate_certificate(model['cohort_user'].user)
    #     token_pattern = re.compile("^[0-9a-zA-Z]{,40}$")

    #     self.assertEqual(model['cohort'].current_day, model['certificate'].duration_in_days)
    #     self.assertEqual(len(certificate.__dict__), 15)
    #     self.assertEqual(certificate.id, 1)
    #     self.assertEqual(strings[model['cohort'].language]["Main Instructor"], 'Instructor Principal')
    #     self.assertEqual(certificate.specialty, model['cohort'].certificate.specialty)
    #     self.assertEqual(certificate.academy, model['cohort'].academy)
    #     self.assertEqual(certificate.layout, model['layout_design'])

    #     first_name = model['teacher_cohort_user'].user.first_name
    #     last_name = model['teacher_cohort_user'].user.last_name

    #     self.assertEqual(certificate.signed_by, f'{first_name} {last_name}')
    #     self.assertEqual(certificate.signed_by_role, strings[model['cohort'].language]
    #         ["Main Instructor"])
    #     self.assertEqual(certificate.user, model['cohort_user'].user)
    #     self.assertEqual(certificate.cohort, model['cohort_user'].cohort)
    #     # self.assertEqual(certificate.cohort, model['cohort_user'].cohort)
    #     self.assertEqual(certificate.preview_url, None)
    #     self.assertEqual(certificate.is_cleaned, True)
    #     self.assertEqual(len(certificate.token), 40)
    #     self.assertEqual(bool(token_pattern.match(certificate.token)), True)

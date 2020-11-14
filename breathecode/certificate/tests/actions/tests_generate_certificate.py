"""
Tasks tests
"""
import re
from unittest.mock import patch
from django.core.exceptions import ValidationError
from breathecode.admissions.models import Certificate
from ...actions import generate_certificate, strings
from ..mixins import CertificateTestCase
from ....admissions.models import FULLY_PAID, UP_TO_DATE, LATE
# from .mocks import CertificateBreathecodeMock
from ..mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    # GOOGLE_CLOUD_INSTANCES
)


class ActionGenerateCertificateTestCase(CertificateTestCase):
    """Tests action generate_certificate"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_finantial_status_none(self):
        """generate_certificate has error without specialty"""
        self.generate_models()

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except Exception as error:
            self.assertEqual(str(error), 'Payment error, finantial_status=`None`')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_finantial_status_late(self):
        """generate_certificate has error without specialty"""
        self.generate_models(finantial_status=LATE)

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except Exception as error:
            self.assertEqual(str(error), f'Payment error, finantial_status=`{LATE}`')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_no_specialty(self):
        """generate_certificate has error without specialty"""
        self.generate_models(finantial_status=FULLY_PAID)

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user,
                                                  self.cohort_user.cohort), None)

        except Certificate.specialty.RelatedObjectDoesNotExist as error:
            self.assertEqual(str(error), 'Certificate has no specialty.')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_no_specialty_without_layout(self):
        """generate_certificate has error without layout"""
        self.generate_models(finantial_status=FULLY_PAID, specialty=True, finished=True)

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except Exception as error:
            self.assertEqual(str(error), 'Missing a default layout')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_without_finish_cohort(self):
        """generate_certificate has error without main_teacher"""
        self.generate_models(finantial_status=FULLY_PAID, specialty=True, layout=True)

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except Exception as error:
            self.assertEqual(str(error), ('cohort.current_day is not equal to '
                'certificate.duration_in_days'))

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_no_main_teacher(self):
        """generate_certificate has error without main_teacher"""
        self.generate_models(finantial_status=FULLY_PAID, specialty=True, layout=True, finished=True)

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except Exception as error:
            self.assertEqual(str(error), ('This cohort does not have a main teacher, please assign'
                ' it first'))

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_bad_stage(self):
        """generate_certificate has bad stage"""
        self.generate_models(finantial_status=FULLY_PAID, specialty=True, finished=True, layout=True, teacher=True)

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except ValidationError as error:
            self.assertEqual(str(error), ("[\"The student cohort stage has to be 'finished' before"
                " you can issue any certificates\"]"))

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_task_pending(self):
        """generate_certificate"""
        self.generate_models('es', finantial_status=UP_TO_DATE, specialty=True, finished=True,
            layout=True, teacher=True, stage=True, task=True)

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except Exception as error:
            self.assertEqual(str(error), 'The student have 1 pending task')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_lang_en(self):
        """generate_certificate"""
        self.generate_models('en', finantial_status=FULLY_PAID, specialty=True, finished=True, layout=True, teacher=True,
            stage=True)

        certificate = generate_certificate(self.cohort_user.user)
        token_pattern = re.compile("^[0-9a-zA-Z]{,40}$")

        self.assertEqual(self.cohort.current_day, self.certificate.duration_in_days)
        self.assertEqual(len(certificate.__dict__), 15)
        self.assertEqual(certificate.id, 2)
        self.assertEqual(strings[self.cohort.language]["Main Instructor"], 'Main Instructor')
        self.assertEqual(certificate.specialty, self.cohort.certificate.specialty)
        self.assertEqual(certificate.academy, self.cohort.academy)
        self.assertEqual(certificate.layout, self.layout_design)
        self.assertEqual(certificate.signed_by, (f'{self.teacher_cohort_user.user.first_name} '
            f'{self.teacher_cohort_user.user.last_name}'))
        self.assertEqual(certificate.signed_by_role, strings[self.cohort.language]
            ["Main Instructor"])
        self.assertEqual(certificate.user, self.cohort_user.user)
        self.assertEqual(certificate.cohort, self.cohort_user.cohort)
        self.assertEqual(certificate.cohort, self.cohort_user.cohort)
        self.assertEqual(certificate.preview_url, None)
        self.assertEqual(certificate.is_cleaned, True)
        self.assertEqual(len(certificate.token), 40)
        self.assertEqual(bool(token_pattern.match(certificate.token)), True)

        # TODO created_at
        # TODO updated_at

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_lang_es(self):
        """generate_certificate"""
        self.generate_models('es', finantial_status=UP_TO_DATE, specialty=True, finished=True, layout=True, teacher=True, stage=True)
        certificate = generate_certificate(self.cohort_user.user)
        token_pattern = re.compile("^[0-9a-zA-Z]{,40}$")

        self.assertEqual(self.cohort.current_day, self.certificate.duration_in_days)
        self.assertEqual(len(certificate.__dict__), 15)
        self.assertEqual(certificate.id, 2)
        self.assertEqual(strings[self.cohort.language]["Main Instructor"], 'Instructor Principal')
        self.assertEqual(certificate.specialty, self.cohort.certificate.specialty)
        self.assertEqual(certificate.academy, self.cohort.academy)
        self.assertEqual(certificate.layout, self.layout_design)
        self.assertEqual(certificate.signed_by, (f'{self.teacher_cohort_user.user.first_name} '
            f'{self.teacher_cohort_user.user.last_name}'))
        self.assertEqual(certificate.signed_by_role, strings[self.cohort.language]
            ["Main Instructor"])
        self.assertEqual(certificate.user, self.cohort_user.user)
        self.assertEqual(certificate.cohort, self.cohort_user.cohort)
        self.assertEqual(certificate.cohort, self.cohort_user.cohort)
        self.assertEqual(certificate.preview_url, None)
        self.assertEqual(certificate.is_cleaned, True)
        self.assertEqual(len(certificate.token), 40)
        self.assertEqual(bool(token_pattern.match(certificate.token)), True)

        # TODO created_at
        # TODO updated_at

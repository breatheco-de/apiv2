"""
Tasks tests
"""
from breathecode.certificate.models import PERSISTED
import re
from unittest.mock import patch
from django.core.exceptions import ValidationError
from breathecode.admissions.models import Certificate
from breathecode.utils import ValidationException
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
        model = self.generate_models(cohort_user=True, certificate=True, specialty=True, layout_design=True, teacher=True, stage=True)

        certificate = generate_certificate(model['cohort_user'].user)

        first_name = model['teacher_cohort_user'].user.first_name
        last_name = model['teacher_cohort_user'].user.last_name
        expected = [{
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': certificate.id,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': f'{first_name} {last_name}',
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'ERROR',
            'status_text': f"The student must have finantial status FULLY_PAID or UP_TO_DATE",
            'user_id': 1,
            'is_cleaned': True,
        }]

        dicts = self.check_all_token(self.all_model_dict([certificate]))
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_finantial_status_late(self):
        """generate_certificate has error without specialty"""
        model = self.generate_models(finantial_status=LATE, cohort_user=True, specialty=True, certificate=True, layout_design=True, teacher=True, stage=True)

        certificate = generate_certificate(model['cohort_user'].user)

        first_name = model['teacher_cohort_user'].user.first_name
        last_name = model['teacher_cohort_user'].user.last_name
        expected = [{
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': certificate.id,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': f'{first_name} {last_name}',
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'ERROR',
            'status_text': f"The student must have finantial status FULLY_PAID or UP_TO_DATE",
            'user_id': 1,
            'is_cleaned': True,
        }]

        dicts = self.check_all_token(self.all_model_dict([certificate]))
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_no_specialty(self):
        """generate_certificate has error without specialty"""
        model = self.generate_models(finantial_status=FULLY_PAID, cohort_user=True)

        try:
            certificate = generate_certificate(model['cohort_user'].user, model['cohort_user'].cohort)
            self.assertEqual(certificate, None)

        except Certificate.specialty.RelatedObjectDoesNotExist as error:
            self.assertEqual(str(error), 'Certificate has no specialty.')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_no_specialty_without_layout(self):
        """generate_certificate has error without layout"""
        model = self.generate_models(finantial_status=FULLY_PAID, specialty=True, finished=True,
            cohort_user=True, certificate=True)

        try:
            certificate = generate_certificate(model['cohort_user'].user, model['cohort_user'].cohort)
            self.assertEqual(certificate, None)

        except ValidationException as error:
            self.assertEqual(str(error), 'Missing a default layout')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_without_finish_cohort(self):
        """generate_certificate without finish cohort"""
        model = self.generate_models(finantial_status=FULLY_PAID, specialty=True, layout_design=True,
            cohort_user=True, certificate=True, teacher=True, stage=True)

        certificate = generate_certificate(model['cohort_user'].user)

        first_name = model['teacher_cohort_user'].user.first_name
        last_name = model['teacher_cohort_user'].user.last_name
        expected = [{
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': certificate.id,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': f'{first_name} {last_name}',
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'ERROR',
            'status_text': f"Cohort current day should be {model['certificate'].duration_in_days}",
            'user_id': 1,
            'is_cleaned': True,
        }]

        dicts = self.check_all_token(self.all_model_dict([certificate]))
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_no_main_teacher(self):
        """generate_certificate has error without main_teacher"""
        model = self.generate_models(finantial_status=FULLY_PAID, specialty=True, layout_design=True,
            finished=True, cohort_user=True, certificate=True)

        try:
            self.assertEqual(generate_certificate(model['cohort_user'].user), None)

        except Exception as error:
            self.assertEqual(str(error), ('This cohort does not have a main teacher, please assign'
                ' it first'))

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_bad_stage(self):
        """generate_certificate has bad stage"""
        model = self.generate_models(finantial_status=FULLY_PAID, specialty=True, finished=True,
            layout_design=True, teacher=True, cohort_user=True, certificate=True)

        certificate = generate_certificate(model['cohort_user'].user)

        first_name = model['teacher_cohort_user'].user.first_name
        last_name = model['teacher_cohort_user'].user.last_name
        expected = [{
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': f'{first_name} {last_name}',
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': 'ERROR',
            'status_text': "The student cohort stage has to be 'finished' before you can issue any certificates",
            'user_id': 1,
            'is_cleaned': True,
        }]

        dicts = self.check_all_token(self.all_model_dict([certificate]))
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_with_task_pending(self):
        """generate_certificate"""
        model = self.generate_models('es', finantial_status=UP_TO_DATE, certificate=True, specialty=True, finished=True,
            layout_design=True, teacher=True, stage=True, task=True, cohort_user=True)
        # print("test_generate_certificate_with_task_pending", model)
        certificate = generate_certificate(model['cohort_user'].user)
        self.assertEqual(certificate.status, 'ERROR')
        self.assertEqual(certificate.status_text, 'The student has 1 pending tasks')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_lang_en(self):
        """generate_certificate"""
        model = self.generate_models('en', finantial_status=FULLY_PAID, specialty=True, finished=True,
            layout_design=True, teacher=True, stage=True, cohort_user=True, certificate=True)

        certificate = generate_certificate(model['cohort_user'].user)

        first_name = model['teacher_cohort_user'].user.first_name
        last_name = model['teacher_cohort_user'].user.last_name
        expected = [{
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': f'{first_name} {last_name}',
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': PERSISTED,
            'status_text': 'Certificate successfully queued for PDF generation',
            'user_id': 1,
            'is_cleaned': True,
        }]

        dicts = self.check_all_token(self.all_user_specialty_dict())

        self.assertEqual(model['cohort'].current_day, model['certificate'].duration_in_days)
        dicts = self.check_all_token(self.all_model_dict([certificate]))
        self.assertEqual(dicts, expected)


    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_lang_es(self):
        """generate_certificate"""
        model = self.generate_models('es', finantial_status=UP_TO_DATE, specialty=True, finished=True,
            layout_design=True, teacher=True, stage=True, cohort_user=True, certificate=True)

        certificate = generate_certificate(model['cohort_user'].user)

        first_name = model['teacher_cohort_user'].user.first_name
        last_name = model['teacher_cohort_user'].user.last_name
        expected = [{
            'academy_id': 1,
            'cohort_id': 1,
            'expires_at': None,
            'id': 1,
            'layout_id': 1,
            'preview_url': None,
            'signed_by': f'{first_name} {last_name}',
            'signed_by_role': strings[model['cohort'].language]["Main Instructor"],
            'specialty_id': 1,
            'status': PERSISTED,
            'status_text': 'Certificate successfully queued for PDF generation',
            'user_id': 1,
            'is_cleaned': True,
        }]

        dicts = self.check_all_token(self.all_user_specialty_dict())

        self.assertEqual(model['cohort'].current_day, model['certificate'].duration_in_days)
        dicts = self.check_all_token(self.all_model_dict([certificate]))
        self.assertEqual(dicts, expected)

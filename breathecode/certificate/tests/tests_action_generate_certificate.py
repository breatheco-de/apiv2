"""
Tasks tests
"""
import re
from unittest.mock import patch
from django.core.exceptions import ValidationError
from breathecode.admissions.models import Certificate
from ..actions import generate_certificate, strings
from .mixins import CertificateTestCase
# from .mocks import CertificateBreathecodeMock
from .mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    # google_cloud_instances
)

class ActionGenerateCertificateTestCase(CertificateTestCase):
    """Tests action generate_certificate"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_no_specialty(self):
        """generate_certificate has error without specialty"""
        self.generate_models_without_specialty()

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user,
                                                  self.cohort_user.cohort), None)

        except Certificate.specialty.RelatedObjectDoesNotExist as error:
            self.assertEqual(str(error), 'Certificate has no specialty.')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_no_specialty_without_cohort(self):
        """generate_certificate has error without cohort"""
        self.generate_models_without_specialty()

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except Certificate.specialty.RelatedObjectDoesNotExist as error:
            self.assertEqual(str(error), 'Certificate has no specialty.')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_no_specialty_without_layout(self):
        """generate_certificate has error without layout"""
        self.generate_models_without_layout()
        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except Exception as error:
            self.assertEqual(str(error), 'Missing a default layout')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate_has_no_main_teacher(self):
        """generate_certificate has error without main_teacher"""
        self.generate_models_without_master_teacher()
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
        self.generate_models_with_stage_ended()
        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except ValidationError as error:
            self.assertEqual(str(error), ("[\"The student cohort stage has to be 'finished' before"
                " you can issue any certificates\"]"))


    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_generate_certificate(self):
        """generate_certificate"""
        self.generate_successful_models()
        certificate = generate_certificate(self.cohort_user.user)
        token_pattern = re.compile("^[0-9a-zA-Z]{,40}$")

        self.assertEqual(len(certificate.__dict__), 15)
        self.assertEqual(certificate.id, 2)
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

        # created_at
        # updated_at

"""
Tasks tests
"""
from django.test import TestCase
from unittest.mock import patch
# from ..tasks import add
from ..actions import certificate_screenshot, generate_certificate, resolve_google_credentials
from .mixins import CertificateTestCase
# from .mocks import CertificateBreathecodeMock
from mixer.backend.django import mixer
from ..models import UserSpecialty
from breathecode.admissions.models import Certificate
from django.core.exceptions import ValidationError
from .mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    google_cloud_instances
)

class AddTestCase(CertificateTestCase):
    def test_resolve_google_credentials_dont_call_open(self):
        """resolve_google_credentials don't call open in development environment"""
        print(resolve_google_credentials())
        self.assertEqual(resolve_google_credentials(), None)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_screenshot_with_invalid_id(self):
        """resolve_google_credentials don't call open in development environment"""
        try:
            certificate_screenshot(0)
        except UserSpecialty.DoesNotExist as error:
            self.assertEqual(str(error), 'UserSpecialty matching query does not exist.')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_screenshot_has_no_specialty(self):
        """resolve_google_credentials don't call open in development environment"""
        self.generate_models_without_specialty()

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user,
                                                  self.cohort_user.cohort), None)

        except Certificate.specialty.RelatedObjectDoesNotExist as error:
            self.assertEqual(str(error), 'Certificate has no specialty.')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_screenshot_has_no_specialty_without_cohort(self):
        """resolve_google_credentials don't call open in development environment"""
        self.generate_models_without_specialty()

        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except Certificate.specialty.RelatedObjectDoesNotExist as error:
            self.assertEqual(str(error), 'Certificate has no specialty.')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_screenshot_has_no_specialty_without_layout(self):
        """resolve_google_credentials don't call open in development environment"""
        self.generate_models_without_layout()
        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except Exception as error:
            self.assertEqual(str(error), 'Missing a default layout')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_screenshot_has_no_main_teacher(self):
        """resolve_google_credentials don't call open in development environment"""
        self.generate_models_without_master_teacher()
        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except Exception as error:
            self.assertEqual(str(error), 'This cohort does not have a main teacher, please assign it first')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_screenshot_has_no_main_teacher(self):
        """resolve_google_credentials don't call open in development environment"""
        self.generate_models_with_stage_ended()
        try:
            self.assertEqual(generate_certificate(self.cohort_user.user), None)

        except ValidationError as error:
            self.assertEqual(str(error), "[\"The student cohort stage has to be 'finished' before you can issue any certificates\"]")


    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_screenshot_has_no_main_teacher2(self):
        """resolve_google_credentials don't call open in development environment"""
        self.generate_successful_models()
        self.assertEqual(generate_certificate(self.cohort_user.user), None)
        # try:

        # except ValidationError as error:
        #     self.assertEqual(str(error), "[\"The student cohort stage has to be 'finished' before you can issue any certificates\"]")

"""
Tasks tests
"""
from unittest.mock import patch, call
from ...tasks import generate_cohort_certificates
from ..mixins import CertificateTestCase
from ..mocks import (
    ACTIONS_PATH,
    ACTIONS_INSTANCES,
    apply_generate_certificate_mock,
)


class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action generate_cohort_certificates"""
    # @patch(ACTIONS_PATH['certificate_screenshot'], apply_certificate_screenshot_mock())
    @patch(ACTIONS_PATH['generate_certificate'], apply_generate_certificate_mock())
    # @patch(ACTIONS_PATH['remove_certificate_screenshot'], apply_remove_certificate_screenshot_mock())
    def test_generate_cohort_certificates_return_true_and_call_certificate_screenshot(self):
        """
        generate_cohort_certificates return_true_and_call_certificate_screenshot, just issue one
        certificate because it's student
        """
        ACTIONS_INSTANCES['generate_certificate'].call_args_list = []
        self.generate_models(specialty=True, layout=True, teacher=True, stage=True)

        self.assertEqual(generate_cohort_certificates(self.cohort_user.id), None)

        self.assertEqual(ACTIONS_INSTANCES['generate_certificate'].call_args_list, 
            [call(self.cohort_user.user, self.cohort_user.cohort)])

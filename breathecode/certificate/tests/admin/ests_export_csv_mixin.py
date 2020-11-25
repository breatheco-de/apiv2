"""
Admin tests
"""
from unittest.mock import patch, call
from ...admin import BadgeAdmin
from ...models import Certificate
from ..mixins import CertificateTestCase
from ..mocks import (
    ACTIONS_PATH,
    ACTIONS_INSTANCES,
    apply_generate_certificate_mock,
)
from pprint import pprint

class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action generate_cohort_certificates"""
    # @patch(ACTIONS_PATH['certificate_screenshot'], apply_certificate_screenshot_mock())
    @patch(ACTIONS_PATH['generate_certificate'], apply_generate_certificate_mock())
    # @patch(ACTIONS_PATH['remove_certificate_screenshot'], apply_remove_certificate_screenshot_mock())
    def test_generate_cohort_certificates_return_true_and_call_certificate_screenshot(self):
        """generate_cohort_certificates don't call open in development environment"""
        # ACTIONS_INSTANCES['generate_certificate'].call_args_list = []

        # self.assertEqual(generate_cohort_certificates(self.cohort_user.id), None)

        # self.assertEqual(ACTIONS_INSTANCES['generate_certificate'].call_args_list,
        #     [call(self.cohort_user.user, self.cohort_user.cohort)])

        csv = BadgeAdmin(Certificate, None)
        # return
        pprint(csv.__dict__)
        self.assertEqual(csv.__dict__, 1)

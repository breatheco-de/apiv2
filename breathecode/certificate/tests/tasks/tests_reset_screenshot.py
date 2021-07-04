"""
Tasks tests
"""
from unittest.mock import patch, call
from ...tasks import reset_screenshot
from ..mixins import CertificateTestCase
from ..mocks import (
    ACTIONS_PATH,
    ACTIONS_INSTANCES,
    apply_certificate_screenshot_mock,
    apply_remove_certificate_screenshot_mock,
)


class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action reset_screenshot"""
    @patch(ACTIONS_PATH['certificate_screenshot'],
           apply_certificate_screenshot_mock())
    @patch(ACTIONS_PATH['remove_certificate_screenshot'],
           apply_remove_certificate_screenshot_mock())
    def test_reset_screenshot_return_true_and_call_certificate_screenshot(
            self):
        """reset_screenshot don't call open in development environment"""
        ACTIONS_INSTANCES['certificate_screenshot'].call_args_list = []
        ACTIONS_INSTANCES['remove_certificate_screenshot'].call_args_list = []

        for number in range(1, 10):
            self.assertEqual(reset_screenshot(number), True)

        self.assertEqual(
            ACTIONS_INSTANCES['remove_certificate_screenshot'].call_args_list,
            [call(number) for number in range(1, 10)])
        self.assertEqual(
            ACTIONS_INSTANCES['certificate_screenshot'].call_args_list,
            [call(number) for number in range(1, 10)])

"""
Tasks tests
"""
from unittest.mock import patch, call
from ...tasks import take_screenshot
from ..mixins import CertificateTestCase
from ..mocks import (
    ACTIONS_PATH,
    ACTIONS_INSTANCES,
    apply_certificate_screenshot_mock,
)


class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action take_screenshot"""
    @patch(ACTIONS_PATH['certificate_screenshot'],
           apply_certificate_screenshot_mock())
    def test_take_screenshot_return_true_and_call_certificate_screenshot(self):
        """take_screenshot don't call open in development environment"""
        ACTIONS_INSTANCES['certificate_screenshot'].call_args_list = []

        for number in range(1, 10):
            self.assertEqual(take_screenshot(number), True)

        self.assertEqual(
            ACTIONS_INSTANCES['certificate_screenshot'].call_args_list,
            [call(number) for number in range(1, 10)])

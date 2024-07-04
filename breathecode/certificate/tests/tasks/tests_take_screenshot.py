"""
Tasks tests
"""

from unittest.mock import MagicMock, patch, call
from ...tasks import take_screenshot
from ..mixins import CertificateTestCase
import breathecode.certificate.actions as actions


class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action take_screenshot"""

    @patch("breathecode.certificate.actions.certificate_screenshot", MagicMock())
    def test_take_screenshot__call_take_screenshot_properly(self):
        take_screenshot(1)
        self.assertEqual(actions.certificate_screenshot.call_args_list, [call(1)])

    @patch("breathecode.certificate.actions.certificate_screenshot", MagicMock(side_effect=Exception()))
    def test_take_screenshot__take_screenshot_raise_a_exception(self):
        take_screenshot(1)
        self.assertEqual(actions.certificate_screenshot.call_args_list, [call(1)])

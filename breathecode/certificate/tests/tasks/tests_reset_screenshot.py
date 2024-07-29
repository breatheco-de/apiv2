"""
Tasks tests
"""

from unittest.mock import MagicMock, patch, call
from ...tasks import reset_screenshot
from ..mixins import CertificateTestCase
import breathecode.certificate.actions as actions


class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action reset_screenshot"""

    @patch("breathecode.certificate.actions.certificate_screenshot", MagicMock())
    @patch("breathecode.certificate.actions.remove_certificate_screenshot", MagicMock())
    def test_reset_screenshot__call_all_properly(self):
        """reset_screenshot don't call open in development environment"""

        reset_screenshot.delay(1)

        self.assertEqual(actions.certificate_screenshot.call_args_list, [call(1)])
        self.assertEqual(actions.remove_certificate_screenshot.call_args_list, [call(1)])

    @patch("breathecode.certificate.actions.certificate_screenshot", MagicMock(side_effect=Exception()))
    @patch("breathecode.certificate.actions.remove_certificate_screenshot", MagicMock())
    def test_reset_screenshot__certificate_screenshot_raise_a_exception(self):
        """reset_screenshot don't call open in development environment"""

        reset_screenshot.delay(1)

        self.assertEqual(actions.certificate_screenshot.call_args_list, [call(1)])
        self.assertEqual(actions.remove_certificate_screenshot.call_args_list, [call(1)])

    @patch("breathecode.certificate.actions.certificate_screenshot", MagicMock())
    @patch("breathecode.certificate.actions.remove_certificate_screenshot", MagicMock(side_effect=Exception()))
    def test_reset_screenshot__remove_certificate_screenshot_raise_a_exception(self):
        """reset_screenshot don't call open in development environment"""

        reset_screenshot.delay(1)

        self.assertEqual(actions.certificate_screenshot.call_args_list, [])
        self.assertEqual(actions.remove_certificate_screenshot.call_args_list, [call(1)])

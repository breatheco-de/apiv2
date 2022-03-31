"""
Tasks tests
"""
from unittest.mock import MagicMock, patch, call
from ...tasks import remove_screenshot
from ..mixins import CertificateTestCase
import breathecode.certificate.actions as actions


class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action remove_screenshot"""
    @patch('breathecode.certificate.actions.remove_certificate_screenshot', MagicMock())
    def test_remove_screenshot__call_all_properly(self):
        """remove_screenshot don't call open in development environment"""

        result = remove_screenshot(1)

        self.assertTrue(result)
        self.assertEqual(actions.remove_certificate_screenshot.call_args_list, [call(1)])

    @patch('breathecode.certificate.actions.remove_certificate_screenshot',
           MagicMock(side_effect=Exception()))
    def test_remove_screenshot__remove_certificate_screenshot_raise_a_exception(self):
        """remove_screenshot don't call open in development environment"""

        result = remove_screenshot(1)

        self.assertFalse(result)
        self.assertEqual(actions.remove_certificate_screenshot.call_args_list, [call(1)])

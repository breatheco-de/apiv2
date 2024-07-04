"""
Tasks tests
"""

from unittest.mock import patch, call, MagicMock

from ...mixins import CertificateTestCase
from ....management.commands.set_default_issued_at import Command


class SetDefaultIssuedAtTestCase(CertificateTestCase):

    @patch("breathecode.certificate.actions.certificate_set_default_issued_at", MagicMock())
    def test_default_issued_at__checking_function_is_being_called(self):
        """certificate_screenshot don't call open in development environment"""
        from breathecode.certificate.actions import certificate_set_default_issued_at

        instance = Command()
        result = instance.handle()

        self.assertEqual(certificate_set_default_issued_at.call_args_list, [call()])
        self.assertEqual(result, None)

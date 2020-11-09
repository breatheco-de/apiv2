"""
Tasks tests
"""
# from ..tasks import add
from ...actions import resolve_google_credentials
from ..mixins import CertificateTestCase

class ActionResolveGoogleCredentialsTestCase(CertificateTestCase):
    """Tests action resolve_google_credentials"""

    def test_resolve_google_credentials_dont_call_open(self):
        """resolve_google_credentials don't call open in development environment"""
        print(resolve_google_credentials())
        self.assertEqual(resolve_google_credentials(), None)

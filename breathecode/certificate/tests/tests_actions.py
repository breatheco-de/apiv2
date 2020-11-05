"""
Tasks tests
"""
from django.test import TestCase
from unittest import mock
# from ..tasks import add
from ..actions import certificate_screenshot, generate_certificate
from .mixins import CertificateTestCase
from .mocks import CertificateBreathecodeMock

class AddTestCase(CertificateTestCase):

    @mock.patch('breathecode.activity.utils.resolve_google_credentials',
        CertificateBreathecodeMock.apply_resolve_google_credentials_mock())
    @mock.patch('breathecode.admissions.actions.resolve_google_credentials',
        CertificateBreathecodeMock.apply_resolve_google_credentials_mock())
    @mock.patch('breathecode.certificate.actions.resolve_google_credentials',
        CertificateBreathecodeMock.apply_resolve_google_credentials_mock())
    def test_certificate_but_is_incomplete(self):
        """Test that the ``add`` task runs with no errors,
        and returns the correct result."""
        # print('aaaaaaaaaaaaaaaaaaaaa1', certificate_screenshot(123))
        # print('aaaaaaaaaaaaaaaaaaaaa2', certificate_screenshot(1))

    # def test_certificate_but_is_incomplet(self):
    #     """Test that the ``add`` task runs with no errors,
    #     and returns the correct result."""
    #     print('aaaaaaaaaaaaaaaaaaaaa3', generate_certificate(self.user, self.cohort_user))
    #     # print(resolve_google_credentials())

"""
Tasks tests
"""
from unittest.mock import patch
from ..actions import certificate_screenshot
from .mixins import CertificateTestCase
from ..models import UserSpecialty
from .mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)

class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """tests_action_certificate_screenshot"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_screenshot_with_invalid_id(self):
        """resolve_google_credentials don't call open in development environment"""
        try:
            certificate_screenshot(0)
        except UserSpecialty.DoesNotExist as error:
            self.assertEqual(str(error), 'UserSpecialty matching query does not exist.')

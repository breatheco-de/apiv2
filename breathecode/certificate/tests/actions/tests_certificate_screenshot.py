"""
Tasks tests
"""
from unittest.mock import patch
from ...actions import certificate_screenshot
from ..mixins import CertificateTestCase
from ...models import UserSpecialty
from ..mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    SCREENSHOTMACHINE_PATH,
    apply_requests_get_mock,
)

class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action certificate_screenshot"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_certificate_screenshot_with_invalid_id(self):
        """certificate_screenshot don't call open in development environment"""
        try:
            certificate_screenshot(0)
        except UserSpecialty.DoesNotExist as error:
            self.assertEqual(str(error), 'UserSpecialty matching query does not exist.')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(SCREENSHOTMACHINE_PATH['get'], apply_requests_get_mock())
    def test_certificate_screenshot_with_invalid_id2(self):
        """certificate_screenshot don't call open in development environment"""
        self.generate_successful_models()
        self.assertEqual(certificate_screenshot(self.certificate.id), None)

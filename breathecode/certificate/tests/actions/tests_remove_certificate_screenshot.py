"""
Tasks tests
"""
from unittest.mock import patch
from ...actions import remove_certificate_screenshot
from ..mixins import CertificateTestCase
from ...models import UserSpecialty
from ..mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    SCREENSHOTMACHINE_PATH,
    apply_screenshotmachine_requests_get_mock,
    CREDENTIALS_PATH,
    apply_resolve_credentials_mock,
)


class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action remove_certificate_screenshot"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_remove_certificate_screenshot_with_invalid_id(self):
        """remove_certificate_screenshot don't call open in development environment"""
        try:
            remove_certificate_screenshot(0)
        except UserSpecialty.DoesNotExist as error:
            self.assertEqual(str(error),
                             'UserSpecialty matching query does not exist.')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(SCREENSHOTMACHINE_PATH['get'],
           apply_screenshotmachine_requests_get_mock())
    @patch(CREDENTIALS_PATH['resolve_credentials'],
           apply_resolve_credentials_mock())
    def test_remove_certificate_screenshot_with_valid_id_cover_else_path(self):
        """remove_certificate_screenshot don't call open in development environment"""
        model = self.generate_models(specialty=True,
                                     layout_design=True,
                                     teacher=True,
                                     stage=True,
                                     user_specialty=True)
        print("ewwowowowowoowowow", model['user_specialty'].preview_url)
        self.assertEqual(
            remove_certificate_screenshot(model['user_specialty'].id), True)

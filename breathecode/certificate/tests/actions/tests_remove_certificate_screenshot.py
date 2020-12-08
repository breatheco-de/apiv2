"""
Tasks tests
"""
from unittest.mock import patch, call
from breathecode.tests.mocks import (
    CELERY_PATH,
    apply_celery_shared_task_mock,
)

from ...actions import remove_certificate_screenshot
from ..mixins import CertificateTestCase
from ...models import UserSpecialty
from ..mocks import (
    GOOGLE_CLOUD_PATH,
    GOOGLE_CLOUD_INSTANCES,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    SCREENSHOTMACHINE_PATH,
    apply_requests_get_mock,
    CREDENTIALS_PATH,
    CREDENTIALS_INSTANCES,
    apply_resolve_credentials_mock,
)


class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action remove_certificate_screenshot"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(CELERY_PATH['shared_task'], apply_celery_shared_task_mock())
    def test_remove_certificate_screenshot_with_invalid_id(self):
        """remove_certificate_screenshot don't call open in development environment"""
        try:
            remove_certificate_screenshot(0)
        except UserSpecialty.DoesNotExist as error:
            self.assertEqual(str(error), 'UserSpecialty matching query does not exist.')

        # self.assertEqual(len(GOOGLE_CLOUD_INSTANCES['client'].call_args_list), 38)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(SCREENSHOTMACHINE_PATH['get'], apply_requests_get_mock())
    @patch(CELERY_PATH['shared_task'], apply_celery_shared_task_mock())
    def test_remove_certificate_screenshot_with_valid_id(self):
        """remove_certificate_screenshot don't call open in development environment"""
        self.generate_models(specialty=True, layout=True, teacher=True, stage=True)
        self.assertEqual(remove_certificate_screenshot(self.certificate.id), False)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(SCREENSHOTMACHINE_PATH['get'], apply_requests_get_mock())
    @patch(CREDENTIALS_PATH['resolve_credentials'], apply_resolve_credentials_mock())
    @patch(CELERY_PATH['shared_task'], apply_celery_shared_task_mock())
    def test_remove_certificate_screenshot_with_valid_id_cover_else_path(self):
        """remove_certificate_screenshot don't call open in development environment"""
        self.generate_models(specialty=True, layout=True, teacher=True, stage=True)

        certificate = UserSpecialty.objects.get(id=self.certificate.id)
        certificate.preview_url = 'asdasdasd'
        certificate.save()

        self.assertEqual(remove_certificate_screenshot(self.certificate.id), True)

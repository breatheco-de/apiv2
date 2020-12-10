"""
Tasks tests
"""
import sys
from unittest.mock import patch, call
from breathecode.tests.mocks import (
    CELERY_PATH,
    apply_celery_shared_task_mock,
)

from ...actions import certificate_screenshot
from ..mixins import CertificateTestCase
from ...models import UserSpecialty
from ..mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    SCREENSHOTMACHINE_INSTANCES,
    SCREENSHOTMACHINE_PATH,
    apply_requests_get_mock,
)

class ActionCertificateScreenshotTestCase(CertificateTestCase):
    """Tests action certificate_screenshot"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(SCREENSHOTMACHINE_PATH['get'], apply_requests_get_mock())
    @patch(CELERY_PATH['shared_task'], apply_celery_shared_task_mock())
    @patch('django.dispatch.receiver', apply_celery_shared_task_mock())
    def test_certificate_screenshot_with_invalid_id(self):
        """certificate_screenshot don't call open in development environment"""
        SCREENSHOTMACHINE_INSTANCES['get'].call_args_list = []
        # print('===================================================================================')
        # print('===================================================================================')
        # print('===================================================================================')
        # print('===================================================================================')
        # print('===================================================================================')
        # print(CELERY_PATH['shared_task'] in sys.modules)
        # print('django.dispatch.receiver' in sys.modules)
        # print([v for v in sys.modules.keys() if v.find('celery.') != -1])
        # print([v for v in sys.modules.keys() if v.find("django.dispatch") != -1])
        # print([k for v, k in sys.modules])
        # print('===================================================================================')
        # print('===================================================================================')
        # print('===================================================================================')
        # print('===================================================================================')
        # print('===================================================================================')

        try:
            certificate_screenshot(0)
        except UserSpecialty.DoesNotExist as error:
            self.assertEqual(str(error), 'UserSpecialty matching query does not exist.')

        self.assertEqual(SCREENSHOTMACHINE_INSTANCES['get'].call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(SCREENSHOTMACHINE_PATH['get'], apply_requests_get_mock())
    @patch(CELERY_PATH['shared_task'], apply_celery_shared_task_mock())
    def test_certificate_screenshot_with_valid_id(self):
        """certificate_screenshot don't call open in development environment"""
        SCREENSHOTMACHINE_INSTANCES['get'].call_args_list = []

        self.generate_models(specialty=True, layout=True, teacher=True, stage=True)
        url = self.generate_screenshotmachine_url()

        self.assertEqual(certificate_screenshot(self.certificate.id), None)
        self.assertEqual(SCREENSHOTMACHINE_INSTANCES['get'].call_args_list, [call(url,
            stream=True)])
        self.assertEqual(self.user_specialty_has_preview_url(self.certificate.id), True)

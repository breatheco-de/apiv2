"""
Test /answer
"""
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    REQUESTS_PATH,
    apply_requests_get_mock,
)
from ..mixins import MediaTestCase

class MediaTestSuite(MediaTestCase):
    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_file_id_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato')
        url = reverse_lazy('media:file_id', kwargs={'media_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Resource not found',
            'status_code': 404
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_file_id_without_data_with_mask_true(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato')
        url = reverse_lazy('media:file_id', kwargs={'media_id': 1}) + '?mask=true'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Resource not found',
            'status_code': 404
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_file_id(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato', media=True)
        url = reverse_lazy('media:file_id', kwargs={'media_id': 1})
        response = self.client.get(url)

        self.assertEqual(response.url, model['media'].url)
        self.assertEqual(response.status_code, status.HTTP_301_MOVED_PERMANENTLY)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media'),
            'hits': model['media'].hits + 1,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch(REQUESTS_PATH['get'], apply_requests_get_mock([(200, 'https://potato.io', 'ok')]))
    def test_file_id_with_mask_true(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {'url': 'https://potato.io'}
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato', media=True,
            media_kwargs=media_kwargs)
        url = reverse_lazy('media:file_id', kwargs={'media_id': 1}) + '?mask=true'
        response = self.client.get(url)

        self.assertEqual(response.getvalue().decode("utf-8"), 'ok')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media'),
            'hits': model['media'].hits + 1,
        }])

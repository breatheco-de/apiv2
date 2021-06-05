"""
Test /answer
"""
import re, urllib
from unittest.mock import MagicMock, Mock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import MediaTestCase
from mixer.backend.django import mixer

class FileMock():
    def delete(*args, **kwargs):
        pass

file_mock = Mock(side_effect=FileMock)

class StorageMock():
    def file(*args, **kwargs):
        return file_mock

storage_mock = Mock(side_effect=StorageMock)

class MediaTestSuite(MediaTestCase):
    """Test /answer"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resolution_id_delete_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato')
        url = reverse_lazy('media:resolution_id', kwargs={'resolution_id': 1})
        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(json, {'detail': 'Resolution was not found', 'status_code': 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resolution_id_delete(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato', media_resolution=True)
        url = reverse_lazy('media:resolution_id', kwargs={'resolution_id': 1})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [])


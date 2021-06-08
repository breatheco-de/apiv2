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
class MediaTestSuite(MediaTestCase):
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resolution_id_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy('media:resolution_id', kwargs={'resolution_id': 1})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resolution_id_wrong_academy(self):
        """Test /answer without auth"""
        url = reverse_lazy('media:resolution_id', kwargs={'resolution_id': 1})
        response = self.client.delete(url, **{'HTTP_Academy': 1 })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resolution_id_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato')
        url = reverse_lazy('media:resolution_id', kwargs={'resolution_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'resolution-not-found',
            'status_code': 404
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resolution_id_delete_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('media:resolution_id', kwargs={'resolution_id': 1})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.delete(url, data)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: crud_media for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resolution_id_get_without_media(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato', media_resolution=True)
        url = reverse_lazy('media:resolution_id', kwargs={'resolution_id': 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {'detail': 'resolution-media-not-found', 'status_code': 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_id_resolution_get_with_id(self):
        """Test /info/media:id/resolution"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, media_resolution=True, media=True,
            capability='read_media', role='potato', profile_academy=True)
        model_dict = self.remove_dinamics_fields(model['media_resolution'].__dict__)
        url = reverse_lazy('media:resolution_id', kwargs={'resolution_id': 1})
        response = self.client.get(url)
        json = response.json()
        expected = {
            'id': model['media_resolution'].id,
            'hash': model['media'].hash,
            'width': model['media_resolution'].width,
            'height': model['media_resolution'].height,
            'hits': model['media_resolution'].hits,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_media_resolution(), 1)
        self.assertEqual(self.get_media_resolution_dict(1), model_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resolution_id_delete_with_different_academy(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=2)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato', media_resolution=True, media=True)
        url = reverse_lazy('media:resolution_id', kwargs={'resolution_id': 1})
        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: crud_media for academy 2",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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

        self.assertEqual(json, {'detail': 'resolution-not-found', 'status_code': 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resolution_id_delete_without_media(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato', media_resolution=True)
        url = reverse_lazy('media:resolution_id', kwargs={'resolution_id': 1})
        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(json, {'detail': 'resolution-media-not-found', 'status_code': 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_resolution_id_delete(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato', media_resolution=True, media=True)
        url = reverse_lazy('media:resolution_id', kwargs={'resolution_id': 1})
        response = self.client.delete(url)
        

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_resolution_dict(), [])


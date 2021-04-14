"""
Test /answer
"""
import re, urllib, tempfile, os, hashlib
from unittest.mock import MagicMock, Mock, call, patch, mock_open, sentinel
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    GOOGLE_CLOUD_INSTANCES,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import MediaTestCase

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
    def test_info_id_without_auth(self):
        """Test /answer without auth"""
        self.headers(content_disposition='attachment; filename="filename.jpg"')
        url = reverse_lazy('media:upload')
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_id_wrong_academy(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
            content_disposition='attachment; filename="filename.jpg"'
        )
        url = reverse_lazy('media:upload')
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_id_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(
            academy=1,
            content_disposition='attachment; filename="filename.jpg"'
        )
        url = reverse_lazy('media:upload')
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: crud_media for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_id_without_data(self):
        """Test /answer without auth"""
        self.headers(
            academy=1
        )
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato')
        url = reverse_lazy('media:upload')
        data = {}
        # files = {'upload_file': os.urandom(1024)}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Missing file in request',
            'status_code': 400,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_id(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
        )
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato')
        url = reverse_lazy('media:upload')

        file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, 'rb') as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, 'rb') as data:
            response = self.client.put(url, {'name': 'filename.jpg', 'file': data})
            json = response.json()

            self.assertDatetime(json['created_at'])
            self.assertDatetime(json['updated_at'])
            del json['created_at']
            del json['updated_at']

            # hash = json['hash']
            self.assertHash(hash)

            expected = {
                'academy': 1,
                'categories': [],
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename',
                'url': f'https://storage.cloud.google.com/media-breathecode/{hash}'
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(self.all_media_dict(), [{
                'academy_id': 1,
                'hash': hash,
                'hits': 0,
                'id': 1,
                # TODO: this test should be improved
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename',
                'url': f'https://storage.cloud.google.com/media-breathecode/{hash}'
            }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_id_with_media(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
        )

        file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, 'rb') as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        media_kwargs={'hash': hash}
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato', media=True,
            media_kwargs=media_kwargs)
        url = reverse_lazy('media:upload')

        with open(file.name, 'rb') as data:
            response = self.client.put(url, {'name': 'filename.jpg', 'file': data})
            json = response.json()

            self.assertDatetime(json['created_at'])
            self.assertDatetime(json['updated_at'])
            del json['created_at']
            del json['updated_at']

            self.assertHash(hash)

            expected = {
                'academy': model['media'].academy.id,
                'categories': [],
                'hash': hash,
                'hits': model['media'].hits,
                'id': model['media'].id,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename',
                'url': model['media'].url,
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.all_media_dict(), [{
                **self.model_to_dict(model, 'media'),
                'hash': hash,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename',
            }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_id_with_media_with_same_slug(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
        )

        file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, 'rb') as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        media_kwargs={'slug': 'filename'}
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato', media=True,
            media_kwargs=media_kwargs)
        url = reverse_lazy('media:upload')

        with open(file.name, 'rb') as data:
            response = self.client.put(url, {'name': 'filename.jpg', 'file': data})
            json = response.json()
            expected = {'detail': 'slug already exists', 'status_code': 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.all_media_dict(), [{
                **self.model_to_dict(model, 'media'),
            }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_id_categories(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
        )
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato', category=True)
        url = reverse_lazy('media:upload')

        file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, 'rb') as file:
            hash = hashlib.sha256(file.read()).hexdigest()

        with open(file.name, 'rb') as file:
            data = {'name': 'filename.jpg', 'file': file, 'categories': '1'}
            response = self.client.put(url, data, format='multipart')
            json = response.json()

            self.assertDatetime(json['created_at'])
            self.assertDatetime(json['updated_at'])
            del json['created_at']
            del json['updated_at']

            # hash = json['hash']
            self.assertHash(hash)

            expected = {
                'academy': 1,
                'categories': [1],
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename',
                'url': f'https://storage.cloud.google.com/media-breathecode/{hash}'
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(self.all_media_dict(), [{
                'academy_id': 1,
                'hash': hash,
                'hits': 0,
                'id': 1,
                # TODO: this test should be improved
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename',
                'url': f'https://storage.cloud.google.com/media-breathecode/{hash}'
            }])

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_info_id_categories_in_headers(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
            categories=1
        )

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []

        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato', category=True)
        url = reverse_lazy('media:upload')

        file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, 'rb') as file:
            file_bytes = file.read()
            hash = hashlib.sha256(file_bytes).hexdigest()

        with open(file.name, 'rb') as file:
            file_mock.url.return_value = f'https://storage.cloud.google.com/media-breathecode/{hash}'
            file_mock.url.call_args_list = []

            data = {'name': 'filename.jpg', 'file': file}
            response = self.client.put(url, data, format='multipart')
            json = response.json()

            self.assertDatetime(json['created_at'])
            self.assertDatetime(json['updated_at'])
            del json['created_at']
            del json['updated_at']

            # hash = json['hash']
            self.assertHash(hash)

            expected = {
                'academy': 1,
                'categories': [1],
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename',
                'url': f'https://storage.cloud.google.com/media-breathecode/{hash}'
            }

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(self.all_media_dict(), [{
                'academy_id': 1,
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename',
                'url': f'https://storage.cloud.google.com/media-breathecode/{hash}'
            }])

            self.assertEqual(storage_mock.call_args_list, [call()])
            self.assertEqual(file_mock.upload.call_args_list, [call(file_bytes, public=True)])
            self.assertEqual(file_mock.url.call_args_list, [call()])

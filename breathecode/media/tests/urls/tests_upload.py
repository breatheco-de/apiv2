"""
Test /answer
"""
import re
import urllib
import tempfile
import os
import random
import hashlib
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
from breathecode.media.views import MIME_ALLOW


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

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload_without_auth(self):
        """Test /answer without auth"""
        self.headers(content_disposition='attachment; filename="filename.jpg"')

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []

        url = reverse_lazy('media:upload')
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload_wrong_academy(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
            content_disposition='attachment; filename="filename.jpg"'
        )

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []

        url = reverse_lazy('media:upload')
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(
            academy=1,
            content_disposition='attachment; filename="filename.jpg"'
        )

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []

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

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload_without_data(self):
        """Test /answer without auth"""
        self.headers(
            academy=1
        )

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []

        model = self.generate_models(authenticate=True, profile_academy=True,
                                     capability='crud_media', role='potato')
        url = reverse_lazy('media:upload')
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {
            'detail': 'Missing file in request',
            'status_code': 400,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_media_dict(), [])

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
        )

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []
        file_mock.url.return_value = 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'

        model = self.generate_models(authenticate=True, profile_academy=True,
                                     capability='crud_media', role='potato')
        url = reverse_lazy('media:upload')

        file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, 'rb') as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, 'rb') as data:
            response = self.client.put(
                url, {'name': 'filename.png', 'file': data})
            json = response.json()

            self.assertHash(hash)

            expected = [{
                'academy': 1,
                'categories': [],
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/png',
                'name': 'filename.png',
                'slug': 'filename',
                'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
            }]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.all_media_dict(), [{
                'academy_id': 1,
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/png',
                'name': 'filename.png',
                'slug': 'filename',
                'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
            }])

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload_with_media(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
        )

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []
        file_mock.url.return_value = 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'

        file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, 'rb') as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        media_kwargs = {'hash': hash}
        model = self.generate_models(authenticate=True, profile_academy=True,
                                     capability='crud_media', role='potato', media=True,
                                     media_kwargs=media_kwargs)
        url = reverse_lazy('media:upload')

        with open(file.name, 'rb') as data:
            response = self.client.put(
                url, {'name': ['filename.jpg'], 'file': [data]})
            json = response.json()

            self.assertHash(hash)

            expected = [{
                'academy': model['media'].academy.id,
                'categories': [],
                'hash': hash,
                'hits': model['media'].hits,
                'id': model['media'].id,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename-jpg',
                'url': model['media'].url,
            }]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.all_media_dict(), [{
                **self.model_to_dict(model, 'media'),
                'hash': hash,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename-jpg',
            }])

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload_with_media_with_same_slug(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
        )

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []

        file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, 'rb') as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        media_kwargs = {'slug': 'filename'}
        model = self.generate_models(authenticate=True, profile_academy=True,
                                     capability='crud_media', role='potato', media=True,
                                     media_kwargs=media_kwargs)
        url = reverse_lazy('media:upload')

        with open(file.name, 'rb') as data:
            response = self.client.put(
                url, {'name': 'filename.jpg', 'file': data})
            json = response.json()
            expected = {'detail': 'slug already exists', 'status_code': 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.all_media_dict(), [{
                **self.model_to_dict(model, 'media'),
            }])

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload_categories(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
        )

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []
        file_mock.url.return_value = 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'

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

            self.assertHash(hash)

            expected = [{
                'academy': 1,
                'categories': [1],
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename-jpg',
                'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
            }]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.all_media_dict(), [{
                'academy_id': 1,
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename-jpg',
                'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
            }])

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload_categories_in_headers(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
            categories=1
        )

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []

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
            file_mock.url.return_value = 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
            file_mock.url.call_args_list = []

            data = {'name': 'filename.jpg', 'file': file}
            response = self.client.put(url, data, format='multipart')
            json = response.json()

            self.assertHash(hash)

            expected = [{
                'academy': 1,
                'categories': [1],
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename-jpg',
                'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
            }]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.all_media_dict(), [{
                'academy_id': 1,
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/png',
                'name': 'filename.jpg',
                'slug': 'filename-jpg',
                'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
            }])

            self.assertEqual(storage_mock.call_args_list, [call()])
            self.assertEqual(file_mock.upload.call_args_list,
                             [call(file_bytes)])
            self.assertEqual(file_mock.url.call_args_list, [call()])

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload_categories_in_headers___(self):
        """Test /answer without auth"""
        self.headers(
            academy=1,
            categories=1
        )

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []

        model = self.generate_models(authenticate=True, profile_academy=True,
                                     capability='crud_media', role='potato', category=True)
        url = reverse_lazy('media:upload')

        file1 = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        file1.write(os.urandom(1024))
        file1.close()

        file2 = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        file2.write(os.urandom(1024))
        file2.close()

        with open(file1.name, 'rb') as file:
            file_bytes1 = file.read()
            hash1 = hashlib.sha256(file_bytes1).hexdigest()

        with open(file2.name, 'rb') as file:
            file_bytes2 = file.read()
            hash2 = hashlib.sha256(file_bytes2).hexdigest()

        file1 = open(file1.name, 'rb')
        file2 = open(file2.name, 'rb')
        file_mock.url.return_value = 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
        file_mock.url.call_args_list = []

        data = {'name': ['filename1.jpg', 'filename2.jpg'],
                'file': [file1, file2]}
        response = self.client.put(url, data, format='multipart')
        json = response.json()

        expected = [{
            'academy': 1,
            'categories': [1],
            'hash': hash1,
            'hits': 0,
            'id': 1,
            'mime': 'image/png',
            'name': 'filename1.jpg',
            'slug': 'filename1-jpg',
            'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
        }, {
            'academy': 1,
            'categories': [1],
            'hash': hash2,
            'hits': 0,
            'id': 2,
            'mime': 'image/png',
            'name': 'filename2.jpg',
            'slug': 'filename2-jpg',
            'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            'academy_id': 1,
            'hash': hash1,
            'hits': 0,
            'id': 1,
            'mime': 'image/png',
            'name': 'filename1.jpg',
            'slug': 'filename1-jpg',
            'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
        }, {
            'academy_id': 1,
            'hash': hash2,
            'hits': 0,
            'id': 2,
            'mime': 'image/png',
            'name': 'filename2.jpg',
            'slug': 'filename2-jpg',
            'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
        }])

        self.assertEqual(storage_mock.call_args_list, [call(), call()])
        self.assertEqual(file_mock.upload.call_args_list, [
                         call(file_bytes1), call(file_bytes2)])
        self.assertEqual(file_mock.url.call_args_list, [call(), call()])

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload_valid_format(self):
        """Test / valid format"""
        self.headers(
            academy=1,
        )
        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []
        file_mock.url.return_value = 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
        model = self.generate_models(authenticate=True, profile_academy=True,
                                     capability='crud_media', role='potato')
        url = reverse_lazy('media:upload')
        file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        file.write(os.urandom(1024))
        file.close()
        with open(file.name, 'rb') as data:
            hash = hashlib.sha256(data.read()).hexdigest()
        with open(file.name, 'rb') as data:
            response = self.client.put(
                url, {'name': 'filename.jpg', 'file': data})
            json = response.json()
            self.assertHash(hash)
            expected = [{
                'academy': 1,
                'categories': [],
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/jpeg',
                'name': 'filename.jpg',
                'slug': 'filename',
                'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
            }]
            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.all_media_dict(), [{
                'academy_id': 1,
                'hash': hash,
                'hits': 0,
                'id': 1,
                'mime': 'image/jpeg',
                'name': 'filename.jpg',
                'slug': 'filename',
                'url': 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'
            }])

    @patch('breathecode.services.google_cloud.Storage', storage_mock)
    def test_upload_invalid_format(self):
        """Test /invalid format"""
        self.headers(
            academy=1,
        )

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        file_mock.upload.call_args_list = []
        file_mock.url.return_value = 'https://storage.cloud.google.com/media-breathecode/hardcoded_url'

        model = self.generate_models(authenticate=True, profile_academy=True,
                                     capability='crud_media', role='potato')
        url = reverse_lazy('media:upload')

        file = tempfile.NamedTemporaryFile(suffix='.lbs', delete=False)
        file.write(os.urandom(1024))
        file.close()

        with open(file.name, 'rb') as data:
            hash = hashlib.sha256(data.read()).hexdigest()

        with open(file.name, 'rb') as data:
            response = self.client.put(
                url, {'name': 'filename.lbs', 'file': data})

            json = response.json()

            self.assertHash(hash)

            expected = {'detail': f'You can upload only files on the following formats: {",".join(MIME_ALLOW)}',
                        'status_code': 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

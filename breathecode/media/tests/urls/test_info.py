import re, urllib
from unittest.mock import MagicMock, Mock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
import datetime
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

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_put_without_args_in_url_or_bulk(self):
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media',media=True, role='potato')
        url = reverse_lazy('media:info')
        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media'),
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_put_without_id_in_url_or_bulk(self):
        self.headers(academy=1)
        url = reverse_lazy('media:info')
        model = self.generate_models(authenticate=True, media=True,
            profile_academy=True, capability='crud_media', role='potato')
        data = [{
            'slug': 'they-killed-kenny'
        }]
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'id-not-in-bulk',
            'status_code': 400
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media'),
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_media__put__in_bulk__with_one_item(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('media:info')
        model = self.generate_models(authenticate=True, media=True,
            profile_academy=True, capability='crud_media', role='potato')
        data = [{
            'id': model['media'].id,
            'hash': model['media'].hash,
            'slug': 'they-killed-kenny',
            'name': model['media'].name,
            'mime': model['media'].mime
        }]
        response = self.client.put(url, data, format='json')
        json = response.json()

        self.assertEqual(json, [{
            'categories': [],
            'academy': 1,
            'hash': model['media'].hash,
            'hits': model['media'].hits,
            'id': model['media'].id,
            'slug': 'they-killed-kenny',
            'mime': model['media'].mime,
            'name': model['media'].name,
            'thumbnail': None,
            'url': model['media'].url,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            'id': model['media'].id,
            'slug': 'they-killed-kenny',
            'name': model['media'].name,
            'mime': model['media'].mime,
            'url': model['media'].url,
            'thumbnail': None,
            'hash': model['media'].hash,
            'hits': model['media'].hits,
            'academy_id': 1,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_media__put__in_bulk__with_two_item(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('media:info')
        model = [self.generate_models(authenticate=True, media=True,
            profile_academy=True, capability='crud_media', role='potato')]
        base = model[0].copy()
        del base['user']
        del base['profile_academy']
        del base['media']

        model = model + [self.generate_models(media=True, profile_academy=True,
            models=base)]

        data = [{
            'id': 1,
            'hash': model[0]['media'].hash,
            'slug': 'they-killed-kenny',
            'name': model[0]['media'].name,
            'mime': model[0]['media'].mime
        }, {
            'id': 2,
            'hash': model[1]['media'].hash,
            'slug': 'you-bastards',
            'name': model[1]['media'].name,
            'mime': model[1]['media'].mime
        }]
        response = self.client.put(url, data, format='json')
        json = response.json()

        self.assertEqual(json, [{
            'categories': [],
            'academy': 1,
            'hash': model[0]['media'].hash,
            'hits': model[0]['media'].hits,
            'id': 1,
            'slug': 'they-killed-kenny',
            'mime': model[0]['media'].mime,
            'name': model[0]['media'].name,
            'thumbnail': None,
            'url': model[0]['media'].url,
        }, {
            'categories': [],
            'academy': 1,
            'hash': model[1]['media'].hash,
            'hits': model[1]['media'].hits,
            'id': 2,
            'slug': 'you-bastards',
            'mime': model[1]['media'].mime,
            'name': model[1]['media'].name,
            'thumbnail': None,
            'url': model[1]['media'].url,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            'id': 1,
            'slug': 'they-killed-kenny',
            'name': model[0]['media'].name,
            'mime': model[0]['media'].mime,
            'url': model[0]['media'].url,
            'thumbnail': None,
            'hash': model[0]['media'].hash,
            'hits': model[0]['media'].hits,
            'academy_id': 1,
        }, {
            'id': 2,
            'slug': 'you-bastards',
            'name': model[1]['media'].name,
            'mime': model[1]['media'].mime,
            'url': model[1]['media'].url,
            'thumbnail': None,
            'hash': model[1]['media'].hash,
            'hits': model[1]['media'].hits,
            'academy_id': 1,
        }])
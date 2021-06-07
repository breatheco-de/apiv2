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
    def test_info_delete_without_args_in_url_or_bulk(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato')
        url = reverse_lazy('media:info')
        response = self.client.put(url)
        json = response.json()
        expected = {
            'detail': "no-media-id",
            'status_code': 400
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media'),
        }])
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_delete_in_bulk_with_one(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields=['id']

        base = self.generate_models(capability='crud_media', role='potato')
        data = {
            'slug': 'they-killed-kenny',
        }
        ignored_data = {
            'url': 'https://www.google.com/',
            'name': 'they-killed-kenny.exe',
            'mime': 'application/hitman',
            'hits': 9999,
            'mime': '1234567890123456789012345678901234567890123456',
        }
        for field in many_fields:
            model = self.generate_models(authenticate=True, profile_academy=True, 
                media=True, models=base)

            value = getattr(model['cohort'], field)
            media = self.get_media(1)
            url = (reverse_lazy('media:info') + f'?{field}=' +
                str(value))
            response = self.client.put(url, {**data, **ignored_data})
            json = response.json()

            if response.status_code != 200:
                print(response.json())

        self.assertEqual(json, {
            'categories': [],
            'academy': 1,
            'hash': model['media'].hash,
            'hits': model['media'].hits,
            'id': model['media'].id,
            'mime': model['media'].mime,
            'name': model['media'].name,
            'thumbnail': None,
            'url': model['media'].url,
            'created_at': self.datetime_to_iso(model['media'].created_at),
            'updated_at': self.datetime_to_iso(media.updated_at),
            **data,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media'),
            **data,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_delete_in_bulk_with_two(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        many_fields=['id']

        base = self.generate_models(capability='crud_media', role='potato')

        for field in many_fields:
            model1 = self.generate_models(authenticate=True, profile_academy=True, 
                media=True, models=base)

            model2 = self.generate_models(authenticate=True, profile_academy=True, 
                media=True, models=base)

            value1 = getattr(model1['cohort'], field)
            value1 = self.datetime_to_iso(value1) if isinstance(value1, datetime) else value1

            value2 = getattr(model2['cohort'], field)
            value2 = self.datetime_to_iso(value2) if isinstance(value2, datetime) else value2

            url = (reverse_lazy('media:info') + f'?{field}=' +
                str(value1) + ',' + str(value2))
            response = self.client.put(url)

            if response.status_code != 204:
                print(response.json())

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.all_media_dict(), [])
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

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_put_in_bulk_with_one(self):
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

            value = getattr(model['media'], field)
            url = (reverse_lazy('media:info') + f'?{field}=' +
                str(value))
            response = self.client.put(url, {**data, **ignored_data}, format='json')
            json = response.json()

            if response.status_code != 200:
                print(response.json())

        self.assertDatetime(json[0]['updated_at'])
        del json[0]['updated_at']

        self.assertEqual(json, [{
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
            **data,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media'),
            **data,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_info_put_in_bulk_with_two(self):
        self.headers(academy=1)
        many_fields=['id']

        base = self.generate_models(authenticate=True, profile_academy=True,
            capability='crud_media', role='potato')
        del base['user']

        models = [self.generate_models(media=True, models=base) for _ in range(0, 2)]
        url = reverse_lazy('media:info')
        data = [{
            'slug': 'they-killed-kenny',
        } for model in models]
        response = self.client.post(url, data, format='json')
        json = response.json()

        print(json)
        self.assertDatetime(json['updated_at'])
        del json['updated_at']

        self.assertEqual(json, [{
            'categories': [],
            'academy': 1,
            'hash': model1['media'].hash,
            'hits': model1['media'].hits,
            'id': model1['media'].id,
            'mime': model1['media'].mime,
            'name': model1['media'].name,
            'thumbnail': None,
            'url': model1['media'].url,
            'created_at': self.datetime_to_iso(model1['media'].created_at),
            **data,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model1, 'media'),
            **data,
        }])
        del base['user']

        models = [self.generate_models(user=True, models=base) for _ in range(0, 2)]
        url = reverse_lazy('admissions:academy_cohort_user')
        data = [{
            'user':  model['user'].id,
            'cohort':  models[0]['cohort'].id,
        } for model in models]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = [{
            'id': model['user'].id - 1,
            'role': 'STUDENT',
            'user': {
                'id': model['user'].id,
                'first_name': model['user'].first_name,
                'last_name': model['user'].last_name,
                'email': model['user'].email,
            },
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name,
                'never_ends': False,
                'kickoff_date': re.sub(
                    r'\+00:00$', 'Z',
                    model['cohort'].kickoff_date.isoformat()
                ),
                'current_day': model['cohort'].current_day,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'syllabus': None,
                'ending_date': model['cohort'].ending_date,
                'stage': model['cohort'].stage,
                'language': model['cohort'].language,
                'created_at': re.sub(r'\+00:00$', 'Z', model['cohort'].created_at.isoformat()),
                'updated_at': re.sub(r'\+00:00$', 'Z', model['cohort'].updated_at.isoformat()),
            },
        } for model in models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'STUDENT',
            'user_id': 2,
        }, {
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 2,
            'role': 'STUDENT',
            'user_id': 3,
        }])
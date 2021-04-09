"""
Test /answer
"""
import re, urllib
from unittest.mock import patch
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
    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy('media:root')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root_wrong_academy(self):
        """Test /answer without auth"""
        url = reverse_lazy('media:root')
        response = self.client.get(url, **{'HTTP_Academy': 1 })
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('media:root')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: read_media for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato')
        url = reverse_lazy('media:root')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato', media=True)
        url = reverse_lazy('media:root')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [],
            'hash': model['media'].hash,
            'hits': model['media'].hits,
            'id': model['media'].id,
            'mime': model['media'].mime,
            'name': model['media'].name,
            'slug': model['media'].slug,
            'url': model['media'].url
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root_with_category(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato', media=True, category=True)
        url = reverse_lazy('media:root')
        response = self.client.get(url)
        json = response.json()
        self.print_model(model, 'media')
        self.print_model(model, 'category')

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash': model['media'].hash,
            'hits': model['media'].hits,
            'id': model['media'].id,
            'mime': model['media'].mime,
            'name': model['media'].name,
            'slug': model['media'].slug,
            'url': model['media'].url
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root_with_category_with_bad_academy_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato', media=True, category=True)
        url = reverse_lazy('media:root') + '?academy=0'
        response = self.client.get(url)
        json = response.json()
        self.print_model(model, 'media')
        self.print_model(model, 'category')

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root_with_category_with_academy_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato', media=True, category=True)
        url = reverse_lazy('media:root') + '?academy=1'
        response = self.client.get(url)
        json = response.json()
        self.print_model(model, 'media')
        self.print_model(model, 'category')

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash': model['media'].hash,
            'hits': model['media'].hits,
            'id': model['media'].id,
            'mime': model['media'].mime,
            'name': model['media'].name,
            'slug': model['media'].slug,
            'url': model['media'].url
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root_with_category_with_bad_mime_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato', media=True, category=True)
        url = reverse_lazy('media:root') + '?mime=application/hitman'
        response = self.client.get(url)
        json = response.json()
        self.print_model(model, 'media')
        self.print_model(model, 'category')

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media')
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root_with_category_with_mime_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_media', role='potato', media=True, category=True)
        url = reverse_lazy('media:root') + '?mime=' + model['media'].mime
        response = self.client.get(url)
        json = response.json()
        self.print_model(model, 'media')
        self.print_model(model, 'category')

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash': model['media'].hash,
            'hits': model['media'].hits,
            'id': model['media'].id,
            'mime': model['media'].mime,
            'name': model['media'].name,
            'slug': model['media'].slug,
            'url': model['media'].url
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media')
        }])

    def test_root_pagination_with_105(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'student'
        base = self.generate_models(authenticate=True, role=role,
            capability='read_media', profile_academy=True)

        models = [self.generate_models(media=True, models=base)
            for _ in range(0, 105)]
        url = reverse_lazy('media:root')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'categories': [],
            'hash': model['media'].hash,
            'hits': model['media'].hits,
            'id': model['media'].id,
            'mime': model['media'].mime,
            'name': model['media'].name,
            'slug': model['media'].slug,
            'url': model['media'].url
        } for model in models if model['media'].id < 101]

        self.assertEqual(json, expected)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media')
        } for model in models])

    def test_root_pagination_first_five(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'student'
        base = self.generate_models(authenticate=True, role=role,
            capability='read_media', profile_academy=True)

        models = [self.generate_models(media=True, models=base)
            for _ in range(0, 10)]
        url = reverse_lazy('media:root') + '?limit=5&offset=0'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': None,
            'last': 'http://testserver/v1/media/?limit=5&offset=5',
            'next': 'http://testserver/v1/media/?limit=5&offset=5',
            'previous': None,
            'results': [{
                'categories': [],
                'hash': model['media'].hash,
                'hits': model['media'].hits,
                'id': model['media'].id,
                'mime': model['media'].mime,
                'name': model['media'].name,
                'slug': model['media'].slug,
                'url': model['media'].url
            } for model in models if model['media'].id < 6]
        }

        self.assertEqual(json, expected)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media')
        } for model in models])

    def test_root_pagination_last_five(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'student'
        base = self.generate_models(authenticate=True, role=role,
            capability='read_media', profile_academy=True)

        models = [self.generate_models(media=True, models=base)
            for _ in range(0, 10)]
        url = reverse_lazy('media:root') + '?limit=5&offset=5'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': 'http://testserver/v1/media/?limit=5',
            'last': None,
            'next': None,
            'previous': 'http://testserver/v1/media/?limit=5',
            'results': [{
                'categories': [],
                'hash': model['media'].hash,
                'hits': model['media'].hits,
                'id': model['media'].id,
                'mime': model['media'].mime,
                'name': model['media'].name,
                'slug': model['media'].slug,
                'url': model['media'].url
            } for model in models if model['media'].id > 5]
        }

        self.assertEqual(json, expected)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media')
        } for model in models])

    def test_root_pagination_after_last_five(self):
        """Test /academy/student"""
        self.headers(academy=1)
        role = 'student'
        base = self.generate_models(authenticate=True, role=role,
            capability='read_media', profile_academy=True)

        models = [self.generate_models(media=True, models=base)
            for _ in range(0, 10)]
        url = reverse_lazy('media:root') + '?limit=5&offset=10'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': 'http://testserver/v1/media/?limit=5',
            'last': None,
            'next': None,
            'previous': 'http://testserver/v1/media/?limit=5&offset=5',
            'results': []
        }

        self.assertEqual(json, expected)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model, 'media')
        } for model in models])

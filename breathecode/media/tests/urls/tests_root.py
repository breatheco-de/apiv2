"""
Test /answer
"""
import re, urllib
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins import MediaTestCase


class MediaTestSuite(MediaTestCase):
    """Test /answer"""
    """
    🔽🔽🔽 Auth
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy('media:root')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__wrong_academy(self):
        """Test /answer without auth"""
        url = reverse_lazy('media:root')
        response = self.client.get(url, **{'HTTP_Academy': 1})
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__without_capability(self):
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

    """
    🔽🔽🔽 Without data
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      capability='read_media',
                                      role='potato')
        url = reverse_lazy('media:root')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [])

    """
    🔽🔽🔽 With data
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True)
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
            'thumbnail': f'{model.media.url}-thumbnail',
            'url': model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    """
    🔽🔽🔽 Academy in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_bad_academy_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?academy=0'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_academy_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?academy=1'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_two_academy_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_media',
                                    role='potato')

        del base['academy']

        models = [
            self.generate_models(academy=True, media=True, category=True, models=base) for _ in range(0, 2)
        ]

        ordened_models = sorted(models, key=lambda x: x['media'].created_at, reverse=True)

        url = (reverse_lazy('media:root') + '?academy=' + str(models[0]['media'].academy.id) + ',' +
               str(models[1]['media'].academy.id))
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(json, [{
            'categories': [{
                'id': model['category'].id,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        } for model in ordened_models])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')} for model in models])

    """
    🔽🔽🔽 Mime in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_bad_mime_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?mime=application/hitman'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_mime_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?mime=' + model['media'].mime
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_two_mime_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_media',
                                    role='potato')

        models = [self.generate_models(media=True, category=True, models=base) for _ in range(0, 2)]

        ordened_models = sorted(models, key=lambda x: x['media'].created_at, reverse=True)

        url = reverse_lazy('media:root') + '?mime=' + models[0]['media'].mime + ',' + models[1]['media'].mime
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(json, [{
            'categories': [{
                'id': model['category'].id,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        } for model in ordened_models])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')} for model in models])

    """
    🔽🔽🔽 Name in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_bad_name_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?name=hitman'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_name_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?name=' + model['media'].name
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_two_name_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_media',
                                    role='potato')

        models = [self.generate_models(media=True, category=True, models=base) for _ in range(0, 2)]

        ordened_models = sorted(models, key=lambda x: x['media'].created_at, reverse=True)

        url = (reverse_lazy('media:root') + '?name=' + models[0]['media'].name + ',' +
               models[1]['media'].name)
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(json, [{
            'categories': [{
                'id': model['category'].id,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        } for model in ordened_models])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')} for model in models])

    """
    🔽🔽🔽 Slug in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_bad_slug_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?slug=hitman'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_slug_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?slug=' + model['media'].slug
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_two_slug_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_media',
                                    role='potato')

        models = [self.generate_models(media=True, category=True, models=base) for _ in range(0, 2)]

        ordened_models = sorted(models, key=lambda x: x['media'].created_at, reverse=True)

        url = (reverse_lazy('media:root') + '?slug=' + models[0]['media'].slug + ',' +
               models[1]['media'].slug)
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'categories': [{
                'id': model['category'].id,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        } for model in ordened_models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')} for model in models])

    """
    🔽🔽🔽 Id in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_bad_id_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?id=0'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_id_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?id=' + str(model['media'].id)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_two_id_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_media',
                                    role='potato')

        models = [self.generate_models(media=True, category=True, models=base) for _ in range(0, 2)]

        ordened_models = sorted(models, key=lambda x: x['media'].created_at, reverse=True)

        url = (reverse_lazy('media:root') + '?id=' + str(models[0]['media'].id) + ',' +
               str(models[1]['media'].id))
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(json, [{
            'categories': [{
                'id': model['category'].id,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        } for model in ordened_models])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')} for model in models])

    """
    🔽🔽🔽 Categories in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_bad_categories_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?categories=0'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_categories_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?categories=1'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_two_categories_in_querystring__return_nothing(self):
        """Test /answer without auth"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_media',
                                    role='potato')

        models = [self.generate_models(media=True, category=True, models=base) for _ in range(0, 2)]

        url = (reverse_lazy('media:root') + '?categories=1,2')
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(json, [])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')} for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_two_categories_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)

        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_media',
                                    role='potato')

        categories = [self.generate_models(category=True).category for _ in range(0, 2)]

        category1 = categories[0]
        category2 = categories[1]

        media_kwargs = {'categories': [x.id for x in categories]}

        models = [
            self.generate_models(media=True, models=base, media_kwargs=media_kwargs) for _ in range(0, 2)
        ]

        ordened_models = sorted(models, key=lambda x: x['media'].created_at, reverse=True)

        url = (reverse_lazy('media:root') + '?categories=1,2')
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(json, [{
            'categories': [{
                'id': category1.id,
                'medias': 2,
                'name': category1.name,
                'slug': category1.slug,
            }, {
                'id': category2.id,
                'medias': 2,
                'name': category2.name,
                'slug': category2.slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        } for model in ordened_models])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')} for model in models])

    """
    🔽🔽🔽 Type in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_bad_type_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?type=freyja'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_type_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {'mime': 'application/pdf'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True,
                                     media_kwargs=media_kwargs)
        url = reverse_lazy('media:root') + '?type=pdf'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    """
    🔽🔽🔽 Like in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_bad_like_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:root') + '?like=freyja'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_like_in_querystring__like_match_name(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {'name': 'Freyja'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True,
                                     media_kwargs=media_kwargs)
        url = reverse_lazy('media:root') + '?like=fre'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_like_in_querystring__like_match_slug(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {'slug': 'freyja'}
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True,
                                     media_kwargs=media_kwargs)
        url = reverse_lazy('media:root') + '?like=Fre'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [{
                'id': 1,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            },
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    """
    🔽🔽🔽 Sort in querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__with_category__with_sort_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {'name': 'Freyja'}
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_media',
                                    role='potato')

        models = [
            self.generate_models(media=True, category=True, models=base, media_kwargs=media_kwargs)
            for _ in range(2)
        ]

        ordened_models = sorted(models, key=lambda x: x['media'].id, reverse=True)

        url = reverse_lazy('media:root') + '?sort=-id'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'categories': [{
                'id': model['category'].id,
                'medias': 1,
                'name': model['category'].name,
                'slug': model['category'].slug,
            }],
            'hash':
            model['media'].hash,
            'hits':
            model['media'].hits,
            'id':
            model['media'].id,
            'mime':
            model['media'].mime,
            'name':
            model['media'].name,
            'slug':
            model['media'].slug,
            'thumbnail':
            f'{model.media.url}-thumbnail',
            'url':
            model['media'].url,
            'academy': {
                'id': model['academy'].id,
                'slug': model['academy'].slug,
                'name': model['academy'].name,
            }
        } for model in ordened_models])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')} for model in models])

    """
    🔽🔽🔽 Bulk delete
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__delete__without_bulk(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_media',
                                     role='potato',
                                     media=True)

        url = reverse_lazy('media:root')
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__delete__bad_id(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_media',
                                     role='potato',
                                     media=True)
        url = reverse_lazy('media:root') + '?id=0'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, 'media')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__delete(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_media',
                                     role='potato',
                                     media=True)

        url = reverse_lazy('media:root') + '?id=1'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__delete__media_that_belongs_to_a_different_academy(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model1 = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      capability='crud_media',
                                      role='potato',
                                      media=True)

        model2 = self.generate_models(media=True, academy=True)
        url = reverse_lazy('media:root') + '?id=1,2'
        response = self.client.delete(url)
        json = response.json()
        expected = {
            'detail': 'academy-different-than-media-academy',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_media_dict(), [{
            **self.model_to_dict(model1, 'media'),
        }, {
            **self.model_to_dict(model2, 'media'),
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_root__delete__two_media(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='crud_media',
                                    role='potato')

        for _ in range(0, 2):
            self.generate_models(media=True, models=base)

        url = reverse_lazy('media:root') + '?id=1,2'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    def test_root__spy_extensions(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      capability='read_media',
                                      role='potato')

        url = reverse_lazy('media:root')
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['PaginationExtension', 'SortExtension']),
        ])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test_root__spy_extension_arguments(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      capability='read_media',
                                      role='potato')

        url = reverse_lazy('media:root')
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(sort='-created_at', paginate=True),
        ])

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
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_category_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy('media:category')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_category_wrong_academy(self):
        """Test /answer without auth"""
        url = reverse_lazy('media:category')
        response = self.client.get(url, **{'HTTP_Academy': 1})
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_category_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('media:category')
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
    def test_category_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      capability='read_media',
                                      role='potato')
        url = reverse_lazy('media:category')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_category_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_category(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     category=True)
        url = reverse_lazy('media:category')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': 1,
            'medias': 0,
            'name': model['category'].name,
            'slug': model['category'].slug,
        }])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_category_dict(), [{**self.model_to_dict(model, 'category')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_category_with_media(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='read_media',
                                     role='potato',
                                     media=True,
                                     category=True)
        url = reverse_lazy('media:category')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'id': 1,
            'medias': 1,
            'name': model['category'].name,
            'slug': model['category'].slug,
        }])
        self.assertEqual(self.all_category_dict(), [{**self.model_to_dict(model, 'category')}])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_category_post(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     capability='crud_media',
                                     role='potato')
        url = reverse_lazy('media:category')
        data = {
            'name': 'They killed kenny',
            'slug': 'they-killed-kenny',
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'id': 1,
            **data,
        }

        self.assertDatetime(json['created_at'])
        del json['created_at']

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_category_dict(), [expected])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    def test_category__spy_extensions(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      capability='read_media',
                                      role='potato')

        url = reverse_lazy('media:category')
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['PaginationExtension']),
        ])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test_category__spy_extension_arguments(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      capability='read_media',
                                      role='potato')

        url = reverse_lazy('media:category')
        self.client.get(url)

        self.assertEqual(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(paginate=True),
        ])

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

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_resolution_id_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy("media:resolution_id", kwargs={"resolution_id": 1})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_resolution_id_wrong_academy(self):
        """Test /answer without auth"""
        url = reverse_lazy("media:resolution_id", kwargs={"resolution_id": 1})
        response = self.client.delete(url, **{"HTTP_Academy": 1})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_resolution_id_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_media_resolution", role="potato"
        )
        url = reverse_lazy("media:resolution_id", kwargs={"resolution_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {"detail": "resolution-not-found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_resolution_id_delete_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:resolution_id", kwargs={"resolution_id": 1})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.delete(url, data)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "You (user: 1) don't have this capability: crud_media_resolution for academy 1",
                "status_code": 403,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_resolution_id_get_without_media(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_media_resolution",
            role="potato",
            media_resolution=True,
        )
        url = reverse_lazy("media:resolution_id", kwargs={"resolution_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {"detail": "resolution-media-not-found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_resolution_dict(), [])

    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_resolution_id_delete_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media_resolution", role="potato"
        )
        url = reverse_lazy("media:resolution_id", kwargs={"resolution_id": 1})
        response = self.client.delete(url)
        json = response.json()
        self.assertEqual(json, {"detail": "resolution-not-found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_resolution_id_delete_without_media(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_media_resolution",
            role="potato",
            media_resolution=True,
        )
        url = reverse_lazy("media:resolution_id", kwargs={"resolution_id": 1})
        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(json, {"detail": "resolution-media-not-found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_resolution_id_delete(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_media_resolution",
            role="potato",
            media_resolution=True,
            media=True,
            media_kwargs={"hash": "abc"},
            media_resolution_kwargs={"hash": "abc"},
        )
        url = reverse_lazy("media:resolution_id", kwargs={"resolution_id": 1})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_resolution_dict(), [])

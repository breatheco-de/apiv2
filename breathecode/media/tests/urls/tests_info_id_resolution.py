"""
Test /answer
"""

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

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_resolution_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy("media:info_id_resolution", kwargs={"media_id": 1})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_resolution_wrong_academy(self):
        """Test /answer without auth"""
        url = reverse_lazy("media:info_id_resolution", kwargs={"media_id": 1})
        response = self.client.get(url, **{"HTTP_Academy": 1})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_resolution_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:info_id_resolution", kwargs={"media_id": 1})
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "You (user: 1) don't have this capability: read_media_resolution for academy 1",
                "status_code": 403,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_media_resolution", role="potato"
        )
        url = reverse_lazy("media:info_id_resolution", kwargs={"media_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {"detail": "media-not-found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_resolution_get_with_id(self):
        """Test /info/media:id/resolution"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            media_resolution=True,
            media=True,
            capability="read_media_resolution",
            role="potato",
            profile_academy=True,
            media_kwargs={"hash": "abc"},
            media_resolution_kwargs={"hash": "abc"},
        )
        model_dict = self.remove_dinamics_fields(model["media_resolution"].__dict__)
        url = reverse_lazy("media:info_id_resolution", kwargs={"media_id": model["media"].id})
        response = self.client.get(url)
        json = response.json()
        expected = [
            {
                "id": model["media_resolution"].id,
                "hash": model["media"].hash,
                "width": model["media_resolution"].width,
                "height": model["media_resolution"].height,
                "hits": model["media_resolution"].hits,
            }
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_media_resolution(), 1)
        self.assertEqual(self.get_media_resolution_dict(1), model_dict)

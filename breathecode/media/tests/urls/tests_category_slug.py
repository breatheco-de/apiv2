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

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_category_slug_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": "they-killed-kenny"})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_category_slug_wrong_academy(self):
        """Test /answer without auth"""
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": "they-killed-kenny"})
        response = self.client.get(url, **{"HTTP_Academy": 1})
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_category_slug_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": "they-killed-kenny"})
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json, {"detail": "You (user: 1) don't have this capability: read_media for academy 1", "status_code": 403}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_category_slug_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True, profile_academy=True, capability="read_media", role="potato")
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": "they-killed-kenny"})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {"detail": "Category not found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_category_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_root(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_media", role="potato", category=True
        )
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": model["category"].slug})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "id": 1,
                "medias": 0,
                "name": model["category"].name,
                "slug": model["category"].slug,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_category_dict(), [{**self.model_to_dict(model, "category")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_category_slug_with_media(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_media", role="potato", media=True, category=True
        )
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": model["category"].slug})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "id": 1,
                "medias": 1,
                "name": model["category"].name,
                "slug": model["category"].slug,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_category_dict(), [{**self.model_to_dict(model, "category")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_academy_slug_put_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": "they-killed-kenny"})
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_academy_slug_put_wrong_academy(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": "they-killed-kenny"})
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_academy_slug_put_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": "they-killed-kenny"})
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(
            json, {"detail": "You (user: 1) don't have this capability: crud_media for academy 1", "status_code": 403}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_academy_slug_put_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True, profile_academy=True, capability="crud_media", role="potato")
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": "they-killed-kenny"})
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {"detail": "Category not found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_category_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_academy_slug_put(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", category=True
        )
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": model["category"].slug})
        data = {"slug": "they-killed-kenny", "name": "They killed kenny"}
        response = self.client.put(url, data)
        json = response.json()

        category = self.get_category(1)

        self.assertDatetime(json["created_at"])
        del json["created_at"]

        self.assertEqual(
            json,
            {
                "id": 1,
                **data,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_category_dict(),
            [
                {
                    "id": 1,
                    **data,
                }
            ],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_category_slug_delete_with_media(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", media=True, category=True
        )
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": model["category"].slug})
        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(json, {"detail": "Category contain some medias", "status_code": 403})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_category_dict(), [{**self.model_to_dict(model, "category")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_category_slug_delete(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", category=True
        )
        url = reverse_lazy("media:category_slug", kwargs={"category_slug": model["category"].slug})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_category_dict(), [])

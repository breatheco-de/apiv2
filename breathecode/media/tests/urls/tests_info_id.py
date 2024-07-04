"""
Test /answer
"""

from unittest.mock import Mock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import MediaTestCase


class FileMock:

    def delete(*args, **kwargs):
        pass


file_mock = Mock(side_effect=FileMock)


class StorageMock:

    def file(*args, **kwargs):
        return file_mock


storage_mock = Mock(side_effect=StorageMock)


class MediaTestSuite(MediaTestCase):
    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_wrong_academy(self):
        """Test /answer without auth"""
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        response = self.client.get(url, **{"HTTP_Academy": 1})
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
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
    def test_info_id_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True, profile_academy=True, capability="read_media", role="potato")
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {"detail": "Media not found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_root(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_media", role="potato", media=True
        )
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "categories": [],
                "hash": model["media"].hash,
                "hits": model["media"].hits,
                "id": model["media"].id,
                "mime": model["media"].mime,
                "name": model["media"].name,
                "slug": model["media"].slug,
                "thumbnail": f"{model.media.url}-thumbnail",
                "url": model["media"].url,
                "academy": {
                    "id": model["academy"].id,
                    "slug": model["academy"].slug,
                    "name": model["academy"].name,
                },
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, "media")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_with_category(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="read_media", role="potato", media=True, category=True
        )
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "categories": [
                    {
                        "id": 1,
                        "medias": 1,
                        "name": model["category"].name,
                        "slug": model["category"].slug,
                    }
                ],
                "hash": model["media"].hash,
                "hits": model["media"].hits,
                "id": model["media"].id,
                "mime": model["media"].mime,
                "name": model["media"].name,
                "slug": model["media"].slug,
                "thumbnail": f"{model.media.url}-thumbnail",
                "url": model["media"].url,
                "academy": {
                    "id": model["academy"].id,
                    "slug": model["academy"].slug,
                    "name": model["academy"].name,
                },
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, "media")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_put_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_put_wrong_academy(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_put_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
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
    def test_info_id_put_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True, profile_academy=True, capability="crud_media", role="potato")
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        data = {}
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(json, {"detail": "media-not-found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_put_from_different_academy(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", media=True
        )
        model2 = self.generate_models(media=True)
        url = reverse_lazy("media:info_id", kwargs={"media_id": 2})
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(json, {"detail": "different-academy-media-put", "status_code": 400})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_media_dict(), [{**self.model_to_dict(model, "media")}, {**self.model_to_dict(model2, "media")}]
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_put(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", media=True
        )
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        data = {
            "slug": "they-killed-kenny",
            "name": "they-killed-kenny.exe",
        }
        ignored_data = {
            "url": "https://www.google.com/",
            "mime": "application/hitman",
            "hits": 9999,
            "mime": "1234567890123456789012345678901234567890123456",
        }
        response = self.client.put(url, {**data, **ignored_data})
        json = response.json()

        self.assertEqual(
            json,
            {
                "categories": [],
                "academy": 1,
                "hash": model["media"].hash,
                "hits": model["media"].hits,
                "id": model["media"].id,
                "mime": model["media"].mime,
                "name": model["media"].name,
                "thumbnail": None,
                "url": model["media"].url,
                **data,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                    **data,
                }
            ],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_delete_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, profile_academy=True, capability="crud_media", role="potato")
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(json, {"detail": "Media not found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_delete_from_different_academy(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", media=True
        )
        model2 = self.generate_models(media=True)
        url = reverse_lazy("media:info_id", kwargs={"media_id": 2})
        response = self.client.delete(url)
        json = response.json()

        self.assertEqual(json, {"detail": "academy-different-than-media-academy", "status_code": 400})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_media_dict(), [{**self.model_to_dict(model, "media")}, {**self.model_to_dict(model2, "media")}]
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_delete(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", media=True
        )
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_id_delete_with_resolution(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_media",
            role="potato",
            media=True,
            media_resolution=True,
            media_kwargs={"hash": "abc"},
            media_resolution_kwargs={"hash": "abc"},
        )
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [])
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch("breathecode.services.google_cloud.Storage", storage_mock)
    def test_info_id_delete_with_category(self):
        """Test /answer without auth"""
        self.headers(academy=1)

        storage_mock.call_args_list = []
        file_mock.call_args_list = []
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", media=True, category=True
        )
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        response = self.client.delete(url)

        self.assertEqual(storage_mock.call_args_list, [call()])
        self.assertEqual(file_mock.delete.call_args_list, [call()])
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [])

    @patch("breathecode.services.google_cloud.Storage", storage_mock)
    def test_info_id_delete_with_category_with_two_media(self):
        """Test /answer without auth"""
        self.headers(academy=1)

        storage_mock.call_args_list = []
        file_mock.delete.call_args_list = []
        base = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", category=True
        )

        media_kwargs = {"hash": "1234567890123456789012345678901234567890123456"}
        models = [self.generate_models(media=True, media_kwargs=media_kwargs, models=base) for _ in range(0, 2)]
        url = reverse_lazy("media:info_id", kwargs={"media_id": 1})
        response = self.client.delete(url)
        self.assertEqual(storage_mock.call_args_list, [])
        self.assertEqual(file_mock.delete.call_args_list, [])
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(models[1], "media")}])

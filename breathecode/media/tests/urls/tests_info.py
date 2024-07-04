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
    def test_info_put_without_args_in_url_or_bulk(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", media=True, role="potato"
        )
        url = reverse_lazy("media:info")
        response = self.client.put(url)
        json = response.json()
        expected = {"detail": "no-args", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                }
            ],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_put_without_category_in_url_or_bulk(self):
        self.headers(academy=1)
        url = reverse_lazy("media:info")
        model = self.generate_models(
            authenticate=True, media=True, profile_academy=True, capability="crud_media", role="potato"
        )
        data = [{"slug": "they-killed-kenny"}]
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {"detail": "categories-not-in-bulk", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                }
            ],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_put_without_id_in_url_or_bulk(self):
        self.headers(academy=1)
        url = reverse_lazy("media:info")
        model = self.generate_models(
            authenticate=True, media=True, profile_academy=True, capability="crud_media", role="potato", category=True
        )
        data = [{"slug": "they-killed-kenny", "categories": [1]}]
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {"detail": "id-not-in-bulk", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                }
            ],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info__put__in_bulk__without_categories(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:info")
        model = self.generate_models(
            authenticate=True, media=True, profile_academy=True, capability="crud_media", role="potato"
        )
        data = [
            {
                "id": model["media"].id,
                "hash": model["media"].hash,
                "slug": "they-killed-kenny",
                "name": model["media"].name,
                "mime": model["media"].mime,
            }
        ]
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {"detail": "categories-not-in-bulk", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                }
            ],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info__put__in_bulk__with_more_arguments(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:info")
        model = self.generate_models(
            authenticate=True, media=True, profile_academy=True, capability="crud_media", role="potato", category=True
        )
        data = [
            {
                "id": model["media"].id,
                "categories": [1, 2],
                "hash": model["media"].hash,
            }
        ]
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {"detail": "extra-args-bulk-mode", "status_code": 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                }
            ],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info_put_in_bulk_from_different_academy(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", media=True
        )
        model2 = self.generate_models(media=True)
        data = [{"id": 2, "categories": [1]}]
        url = reverse_lazy("media:info")
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(json, {"detail": "different-academy-media-put", "status_code": 400})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_media_dict(), [{**self.model_to_dict(model, "media")}, {**self.model_to_dict(model2, "media")}]
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info__put__in_bulk__with_one_item(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:info")
        model = self.generate_models(
            authenticate=True, media=True, profile_academy=True, capability="crud_media", role="potato", category=True
        )
        data = [{"id": model["media"].id, "categories": [1]}]
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(
            json,
            [
                {
                    "categories": [1],
                    "academy": 1,
                    "hash": model["media"].hash,
                    "hits": model["media"].hits,
                    "id": model["media"].id,
                    "slug": model["media"].slug,
                    "mime": model["media"].mime,
                    "name": model["media"].name,
                    "thumbnail": None,
                    "url": model["media"].url,
                }
            ],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.full_media_dict(),
            [
                {
                    "categories": [
                        {
                            "id": model["category"].id,
                            "medias": 1,
                            "name": model["category"].name,
                            "slug": model["category"].slug,
                        }
                    ],
                    "hash": model["media"].hash,
                    "hits": model["media"].hits,
                    "id": 1,
                    "slug": model["media"].slug,
                    "mime": model["media"].mime,
                    "name": model["media"].name,
                    "thumbnail": f"{model['media'].url}-thumbnail",
                    "url": model["media"].url,
                    "academy": {
                        "id": model["academy"].id,
                        "slug": model["academy"].slug,
                        "name": model["academy"].name,
                    },
                }
            ],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info__put__in_bulk__with_two_item(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("media:info")
        model = [
            self.generate_models(
                authenticate=True,
                media=True,
                profile_academy=True,
                capability="crud_media",
                role="potato",
                category=True,
            )
        ]
        base = model[0].copy()
        del base["user"]
        del base["profile_academy"]
        del base["media"]
        del base["category"]

        model = model + [self.generate_models(media=True, profile_academy=True, category=True, models=base)]

        data = [{"id": 1, "categories": [1, 2]}, {"id": 2, "categories": [1, 2]}]
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(
            json,
            [
                {
                    "categories": [1, 2],
                    "academy": 1,
                    "hash": model[0]["media"].hash,
                    "hits": model[0]["media"].hits,
                    "id": 1,
                    "slug": model[0]["media"].slug,
                    "mime": model[0]["media"].mime,
                    "name": model[0]["media"].name,
                    "thumbnail": None,
                    "url": model[0]["media"].url,
                    "academy": model[0]["academy"].id,
                },
                {
                    "categories": [1, 2],
                    "academy": 1,
                    "hash": model[1]["media"].hash,
                    "hits": model[1]["media"].hits,
                    "id": 2,
                    "slug": model[1]["media"].slug,
                    "mime": model[1]["media"].mime,
                    "name": model[1]["media"].name,
                    "thumbnail": None,
                    "url": model[1]["media"].url,
                    "academy": model[1]["academy"].id,
                },
            ],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.full_media_dict(),
            [
                {
                    "categories": [
                        {
                            "id": model[0]["category"].id,
                            "medias": 2,
                            "name": model[0]["category"].name,
                            "slug": model[0]["category"].slug,
                        },
                        {
                            "id": model[1]["category"].id,
                            "medias": 2,
                            "name": model[1]["category"].name,
                            "slug": model[1]["category"].slug,
                        },
                    ],
                    "hash": model[0]["media"].hash,
                    "hits": model[0]["media"].hits,
                    "id": 1,
                    "slug": model[0]["media"].slug,
                    "mime": model[0]["media"].mime,
                    "name": model[0]["media"].name,
                    "thumbnail": f"{model[0]['media'].url}-thumbnail",
                    "url": model[0]["media"].url,
                    "academy": {
                        "id": model[0]["academy"].id,
                        "slug": model[0]["academy"].slug,
                        "name": model[0]["academy"].name,
                    },
                },
                {
                    "categories": [
                        {
                            "id": model[0]["category"].id,
                            "medias": 2,
                            "name": model[0]["category"].name,
                            "slug": model[0]["category"].slug,
                        },
                        {
                            "id": model[1]["category"].id,
                            "medias": 2,
                            "name": model[1]["category"].name,
                            "slug": model[1]["category"].slug,
                        },
                    ],
                    "hash": model[1]["media"].hash,
                    "hits": model[1]["media"].hits,
                    "id": 2,
                    "slug": model[1]["media"].slug,
                    "mime": model[1]["media"].mime,
                    "name": model[1]["media"].name,
                    "thumbnail": f"{model[1]['media'].url}-thumbnail",
                    "url": model[1]["media"].url,
                    "academy": {
                        "id": model[1]["academy"].id,
                        "slug": model[1]["academy"].slug,
                        "name": model[1]["academy"].name,
                    },
                },
            ],
        )

    """
    🔽🔽🔽 Bulk delete
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info__delete__without_bulk(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", media=True
        )

        url = reverse_lazy("media:info")
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, "media")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info__delete__bad_id(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", media=True
        )
        url = reverse_lazy("media:info") + "?id=0"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [{**self.model_to_dict(model, "media")}])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info__delete(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", media=True
        )

        url = reverse_lazy("media:info") + "?id=1"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info__delete__media_that_belongs_to_a_different_academy(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model1 = self.generate_models(
            authenticate=True, profile_academy=True, capability="crud_media", role="potato", media=True
        )

        model2 = self.generate_models(media=True, academy=True)
        url = reverse_lazy("media:info") + "?id=1,2"
        response = self.client.delete(url)
        json = response.json()
        expected = {
            "detail": "academy-different-than-media-academy",
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model1, "media"),
                },
                {
                    **self.model_to_dict(model2, "media"),
                },
            ],
        )

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_info__delete__two_media(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True, profile_academy=True, capability="crud_media", role="potato")

        for _ in range(0, 2):
            self.generate_models(media=True, models=base)

        url = reverse_lazy("media:info") + "?id=1,2"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_media_dict(), [])

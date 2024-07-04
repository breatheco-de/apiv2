"""
Test /answer
"""

from breathecode.tests.mocks.requests import apply_requests_request_mock
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_get_mock,
)
from ..mixins import MediaTestCase

RESIZE_IMAGE_URL = "https://us-central1-labor-day-story.cloudfunctions.net/resize-image"


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


def bad_mime_response():
    data = {"message": "File type not allowed", "status_code": 400}
    return (400, RESIZE_IMAGE_URL, data)


def bad_size_response():
    data = {"message": "Incorrect width or height", "status_code": 400}
    return (400, RESIZE_IMAGE_URL, data)


def bad_server_response():
    data = {"message": "They killed Kenny", "status_code": 400}
    return (500, RESIZE_IMAGE_URL, data)


def resized_response(width=1000, height=1000):
    data = {"message": "Ok", "status_code": 200, "width": width, "height": height}
    return (200, RESIZE_IMAGE_URL, data)


# MEDIA_GALLERY_BUCKET
@patch.dict("os.environ", {"GOOGLE_CLOUD_TOKEN": "blablabla"})
class MediaTestSuite(MediaTestCase):
    """Test /answer"""

    """
    🔽🔽🔽 Without data
    """

    def test_file_id__without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(academy=True)
        url = reverse_lazy("media:file_id", kwargs={"media_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {"detail": "Resource not found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_dict(), [])
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id__without_data__with_mask_true(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(academy=True)
        url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?mask=true"
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {"detail": "Resource not found", "status_code": 404})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_media_dict(), [])
        self.assertEqual(self.all_media_resolution_dict(), [])

    """
    🔽🔽🔽 With data
    """

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(academy=True, media=True)
        url = reverse_lazy("media:file_id", kwargs={"media_id": 1})
        response = self.client.get(url)

        self.assertEqual(response.url, model["media"].url)
        self.assertEqual(response.status_code, status.HTTP_301_MOVED_PERMANENTLY)
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                    "hits": model["media"].hits + 1,
                }
            ],
        )
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    @patch(REQUESTS_PATH["get"], apply_requests_get_mock([(200, "https://potato.io", "ok")]))
    def test_file_id_with_mask_true(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {"url": "https://potato.io"}
        model = self.generate_models(academy=True, media=True, media_kwargs=media_kwargs)
        url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?mask=true"
        response = self.client.get(url)

        self.assertEqual(response.getvalue().decode("utf-8"), "ok")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                    "hits": model["media"].hits + 1,
                }
            ],
        )
        self.assertEqual(self.all_media_resolution_dict(), [])

    """
    🔽🔽🔽 Width in querystring
    """

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id__with_width_in_querystring__bad_mime(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {"url": "https://potato.io", "mime": "application/json"}
        model = self.generate_models(academy=True, media=True, media_kwargs=media_kwargs)
        url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?width=1000"
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "cannot-resize-media", "status_code": 400}

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
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id__with_width_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {"url": "https://potato.io/harcoded", "mime": "image/png", "hash": "harcoded"}
        model = self.generate_models(academy=True, media=True, media_kwargs=media_kwargs)

        with patch("google.oauth2.id_token.fetch_id_token") as token_mock:
            token_mock.return_value = "blablabla"

            with patch(REQUESTS_PATH["request"], apply_requests_request_mock([resized_response()])) as mock:
                url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?width=1000"
                response = self.client.get(url)

        self.assertEqual(response.url, "https://potato.io/harcoded-1000x1000")
        self.assertEqual(response.status_code, status.HTTP_301_MOVED_PERMANENTLY)

        self.assertEqual(
            mock.call_args_list,
            [
                call(
                    "POST",
                    "https://us-central1-labor-day-story.cloudfunctions.net/resize-image",
                    data='{"width": "1000", "height": null, "filename": "harcoded", "bucket": "bucket-name"}',
                    headers={
                        "Authorization": "Bearer blablabla",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    params={},
                    timeout=2,
                )
            ],
        )

        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                    "hits": model["media"].hits + 1,
                }
            ],
        )

        self.assertEqual(
            self.all_media_resolution_dict(),
            [
                {
                    "hash": model.media.hash,
                    "height": 1000,
                    "hits": 1,
                    "id": 1,
                    "width": 1000,
                }
            ],
        )

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id__with_width_in_querystring__resolution_exist(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {"url": "https://potato.io/harcoded", "mime": "image/png", "hash": "harcoded"}
        media_resolution_kwargs = {"width": 1000, "height": 1000, "hash": "harcoded"}
        model = self.generate_models(
            academy=True,
            media=True,
            media_resolution=True,
            media_kwargs=media_kwargs,
            media_resolution_kwargs=media_resolution_kwargs,
        )

        with patch(REQUESTS_PATH["request"], apply_requests_request_mock([resized_response()])) as mock:
            url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?width=1000"
            response = self.client.get(url)

        self.assertEqual(response.url, "https://potato.io/harcoded-1000x1000")
        self.assertEqual(response.status_code, status.HTTP_301_MOVED_PERMANENTLY)

        self.assertEqual(mock.call_args_list, [])
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                    "hits": model["media"].hits + 1,
                }
            ],
        )

        self.assertEqual(
            self.all_media_resolution_dict(),
            [
                {
                    **self.model_to_dict(model, "media_resolution"),
                    "hits": model["media_resolution"].hits + 1,
                }
            ],
        )

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id__with_width_in_querystring__bad_mime(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {"url": "https://potato.io/harcoded", "mime": "image/png", "hash": "harcoded"}
        model = self.generate_models(academy=True, media=True, media_kwargs=media_kwargs)

        with patch("google.oauth2.id_token.fetch_id_token") as token_mock:
            token_mock.return_value = "blablabla"

            with patch(REQUESTS_PATH["request"], apply_requests_request_mock([bad_size_response()])) as mock:
                url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?width=1000"
                response = self.client.get(url)
                json = response.json()

        expected = {
            "detail": "cloud-function-bad-input",
            "status_code": 500,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.assertEqual(
            mock.call_args_list,
            [
                call(
                    "POST",
                    "https://us-central1-labor-day-story.cloudfunctions.net/resize-image",
                    data='{"width": "1000", "height": null, "filename": "harcoded", "bucket": "bucket-name"}',
                    headers={
                        "Authorization": "Bearer blablabla",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    params={},
                    timeout=2,
                )
            ],
        )

        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                    "hits": model["media"].hits + 1,
                }
            ],
        )

        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id__with_width_in_querystring__cloud_function_error(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {"url": "https://potato.io/harcoded", "mime": "image/png", "hash": "harcoded"}
        model = self.generate_models(academy=True, media=True, media_kwargs=media_kwargs)

        with patch("google.oauth2.id_token.fetch_id_token") as token_mock:
            token_mock.return_value = "blablabla"

            with patch(REQUESTS_PATH["request"], apply_requests_request_mock([bad_server_response()])) as mock:
                url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?width=1000"
                response = self.client.get(url)
                json = response.json()

        expected = {
            "detail": "cloud-function-bad-input",
            "status_code": 500,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.assertEqual(
            mock.call_args_list,
            [
                call(
                    "POST",
                    "https://us-central1-labor-day-story.cloudfunctions.net/resize-image",
                    data='{"width": "1000", "height": null, "filename": "harcoded", "bucket": "bucket-name"}',
                    headers={
                        "Authorization": "Bearer blablabla",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    params={},
                    timeout=2,
                )
            ],
        )

        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                    "hits": model["media"].hits + 1,
                }
            ],
        )

        self.assertEqual(self.all_media_resolution_dict(), [])

    """
    🔽🔽🔽 Height in querystring
    """

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id__with_height_in_querystring__bad_mime(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {"url": "https://potato.io", "mime": "application/json"}
        model = self.generate_models(academy=True, media=True, media_kwargs=media_kwargs)
        url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?height=1000"
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "cannot-resize-media", "status_code": 400}

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
        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id__with_height_in_querystring(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {"url": "https://potato.io/harcoded", "mime": "image/png", "hash": "harcoded"}
        model = self.generate_models(academy=True, media=True, media_kwargs=media_kwargs)

        with patch("google.oauth2.id_token.fetch_id_token") as token_mock:
            token_mock.return_value = "blablabla"

            with patch(REQUESTS_PATH["request"], apply_requests_request_mock([resized_response()])) as mock:
                url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?height=1000"
                response = self.client.get(url)

        self.assertEqual(response.url, "https://potato.io/harcoded-1000x1000")
        self.assertEqual(response.status_code, status.HTTP_301_MOVED_PERMANENTLY)

        self.assertEqual(
            mock.call_args_list,
            [
                call(
                    "POST",
                    "https://us-central1-labor-day-story.cloudfunctions.net/resize-image",
                    data='{"width": null, "height": "1000", "filename": "harcoded", "bucket": "bucket-name"}',
                    headers={
                        "Authorization": "Bearer blablabla",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    params={},
                    timeout=2,
                )
            ],
        )

        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                    "hits": model["media"].hits + 1,
                }
            ],
        )

        self.assertEqual(
            self.all_media_resolution_dict(),
            [
                {
                    "hash": model.media.hash,
                    "height": 1000,
                    "hits": 1,
                    "id": 1,
                    "width": 1000,
                }
            ],
        )

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id__with_height_in_querystring__resolution_exist(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {"url": "https://potato.io/harcoded", "mime": "image/png", "hash": "harcoded"}
        media_resolution_kwargs = {"width": 1000, "height": 1000, "hash": "harcoded"}
        model = self.generate_models(
            academy=True,
            media=True,
            media_resolution=True,
            media_kwargs=media_kwargs,
            media_resolution_kwargs=media_resolution_kwargs,
        )

        with patch(REQUESTS_PATH["request"], apply_requests_request_mock([resized_response()])) as mock:
            url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?height=1000"
            response = self.client.get(url)

        self.assertEqual(response.url, "https://potato.io/harcoded-1000x1000")
        self.assertEqual(response.status_code, status.HTTP_301_MOVED_PERMANENTLY)

        self.assertEqual(mock.call_args_list, [])
        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                    "hits": model["media"].hits + 1,
                }
            ],
        )

        self.assertEqual(
            self.all_media_resolution_dict(),
            [
                {
                    **self.model_to_dict(model, "media_resolution"),
                    "hits": model["media_resolution"].hits + 1,
                }
            ],
        )

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id__with_height_in_querystring__bad_mime(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {"url": "https://potato.io/harcoded", "mime": "image/png", "hash": "harcoded"}
        model = self.generate_models(academy=True, media=True, media_kwargs=media_kwargs)

        with patch("google.oauth2.id_token.fetch_id_token") as token_mock:
            token_mock.return_value = "blablabla"

            with patch(REQUESTS_PATH["request"], apply_requests_request_mock([bad_size_response()])) as mock:
                url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?height=1000"
                response = self.client.get(url)
                json = response.json()

        expected = {
            "detail": "cloud-function-bad-input",
            "status_code": 500,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.assertEqual(
            mock.call_args_list,
            [
                call(
                    "POST",
                    "https://us-central1-labor-day-story.cloudfunctions.net/resize-image",
                    data='{"width": null, "height": "1000", "filename": "harcoded", "bucket": "bucket-name"}',
                    headers={
                        "Authorization": "Bearer blablabla",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    params={},
                    timeout=2,
                )
            ],
        )

        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                    "hits": model["media"].hits + 1,
                }
            ],
        )

        self.assertEqual(self.all_media_resolution_dict(), [])

    @patch(
        "os.getenv",
        MagicMock(
            side_effect=apply_get_env(
                {
                    "GOOGLE_PROJECT_ID": "labor-day-story",
                    "MEDIA_GALLERY_BUCKET": "bucket-name",
                }
            )
        ),
    )
    def test_file_id__with_height_in_querystring__cloud_function_error(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        media_kwargs = {"url": "https://potato.io/harcoded", "mime": "image/png", "hash": "harcoded"}
        model = self.generate_models(academy=True, media=True, media_kwargs=media_kwargs)

        with patch("google.oauth2.id_token.fetch_id_token") as token_mock:
            token_mock.return_value = "blablabla"

            with patch(REQUESTS_PATH["request"], apply_requests_request_mock([bad_server_response()])) as mock:
                url = reverse_lazy("media:file_id", kwargs={"media_id": 1}) + "?height=1000"
                response = self.client.get(url)
                json = response.json()

        expected = {
            "detail": "cloud-function-bad-input",
            "status_code": 500,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.assertEqual(
            mock.call_args_list,
            [
                call(
                    "POST",
                    "https://us-central1-labor-day-story.cloudfunctions.net/resize-image",
                    data='{"width": null, "height": "1000", "filename": "harcoded", "bucket": "bucket-name"}',
                    headers={
                        "Authorization": "Bearer blablabla",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    params={},
                    timeout=2,
                )
            ],
        )

        self.assertEqual(
            self.all_media_dict(),
            [
                {
                    **self.model_to_dict(model, "media"),
                    "hits": model["media"].hits + 1,
                }
            ],
        )

        self.assertEqual(self.all_media_resolution_dict(), [])

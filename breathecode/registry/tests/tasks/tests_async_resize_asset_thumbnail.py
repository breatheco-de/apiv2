"""
Test /answer
"""

from random import randint
from unittest.mock import MagicMock, call, patch

from breathecode.registry.tasks import async_resize_asset_thumbnail
from breathecode.services.google_cloud import FunctionV1
from logging import Logger
from ..mixins import RegistryTestCase


class Response:

    def __init__(self, response, status_code):
        self.response = response
        self.status_code = status_code

    def json(self):
        return self.response


WIDTH = randint(0, 2000)
HEIGHT = randint(0, 2000)
FUNCTION_GOOD_RESPONSE = Response({"status_code": 200, "message": "Ok", "width": WIDTH, "height": HEIGHT}, 200)
FUNCTION_BAD_RESPONSE = Response({"status_code": 400, "message": "Bad response"}, 400)


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 GET without Media
    """

    @patch("logging.Logger.error", MagicMock())
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
    def test__without_media(self):
        # model = self.bc.database.create(asset=1)
        async_resize_asset_thumbnail.delay(1)

        self.assertEqual(self.bc.database.list_of("media.Media"), [])
        self.assertEqual(self.bc.database.list_of("media.MediaResolution"), [])
        self.assertEqual(Logger.error.call_args_list, [call("Media with id 1 not found")])

    """
    🔽🔽🔽 GET with Media
    """

    @patch("logging.Logger.error", MagicMock())
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
    def test__with_media(self):
        model = self.bc.database.create(media=1)
        async_resize_asset_thumbnail.delay(1)

        self.assertEqual(self.bc.database.list_of("media.Media"), [self.bc.format.to_dict(model.media)])
        self.assertEqual(self.bc.database.list_of("media.MediaResolution"), [])
        self.assertEqual(
            Logger.error.call_args_list,
            [
                call("async_resize_asset_thumbnail needs the width or height parameter"),
            ],
        )

    """
    🔽🔽🔽 GET with Media, passing width and height
    """

    @patch("logging.Logger.error", MagicMock())
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
    def test__with_media__passing_width__passing_height(self):
        model = self.bc.database.create(media=1)
        async_resize_asset_thumbnail.delay(1, width=WIDTH, height=HEIGHT)

        self.assertEqual(self.bc.database.list_of("media.Media"), [self.bc.format.to_dict(model.media)])
        self.assertEqual(self.bc.database.list_of("media.MediaResolution"), [])
        self.assertEqual(
            Logger.error.call_args_list,
            [
                call("async_resize_asset_thumbnail can't be used with width and height together"),
            ],
        )

    """
    🔽🔽🔽 GET with Media, passing width or height, function return good response
    """

    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.services.google_cloud.function_v1.FunctionV1.__init__", MagicMock(return_value=None))
    @patch(
        "breathecode.services.google_cloud.function_v1.FunctionV1.call", MagicMock(return_value=FUNCTION_GOOD_RESPONSE)
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
    def test__with_media__passing_width_or_height__function_return_good_response(self):
        model = self.bc.database.create(media=1)
        cases = [((1,), {"width": WIDTH}, 1), ((1,), {"height": HEIGHT}, 2)]

        for args, kwargs, media_resolution_id in cases:
            async_resize_asset_thumbnail.delay(*args, **kwargs)

            self.assertEqual(self.bc.database.list_of("media.Media"), [self.bc.format.to_dict(model.media)])
            self.assertEqual(
                self.bc.database.list_of("media.MediaResolution"),
                [
                    {
                        "hash": model.media.hash,
                        "height": HEIGHT,
                        "hits": 0,
                        "id": media_resolution_id,
                        "width": WIDTH,
                    }
                ],
            )
            self.assertEqual(Logger.error.call_args_list, [])

            self.assertEqual(
                FunctionV1.__init__.call_args_list,
                [
                    call(region="us-central1", project_id="labor-day-story", name="resize-image"),
                ],
            )

            self.assertEqual(
                str(FunctionV1.call.call_args_list),
                str(
                    [
                        call(
                            {
                                **kwargs,
                                "filename": model.media.hash,
                                "bucket": "bucket-name",
                            }
                        ),
                    ]
                ),
            )

            # teardown
            self.bc.database.delete("media.MediaResolution")
            FunctionV1.__init__.call_args_list = []
            FunctionV1.call.call_args_list = []

    """
    🔽🔽🔽 GET with Media, passing width or height, function return bad response
    """

    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.services.google_cloud.function_v1.FunctionV1.__init__", MagicMock(return_value=None))
    @patch(
        "breathecode.services.google_cloud.function_v1.FunctionV1.call", MagicMock(return_value=FUNCTION_BAD_RESPONSE)
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
    def test__with_media__passing_width_or_height__function_return_bad_response(self):
        model = self.bc.database.create(media=1)
        cases = [((1,), {"width": WIDTH}), ((1,), {"height": HEIGHT})]

        for args, kwargs in cases:
            async_resize_asset_thumbnail.delay(*args, **kwargs)

            self.assertEqual(self.bc.database.list_of("media.Media"), [self.bc.format.to_dict(model.media)])
            self.assertEqual(self.bc.database.list_of("media.MediaResolution"), [])
            self.assertEqual(
                Logger.error.call_args_list,
                [
                    call(
                        "Unhandled error with `resize-image` cloud function, response "
                        "" + str(FUNCTION_BAD_RESPONSE.json()) + ""
                    ),
                ],
            )

            self.assertEqual(
                FunctionV1.__init__.call_args_list,
                [
                    call(region="us-central1", project_id="labor-day-story", name="resize-image"),
                ],
            )

            self.assertEqual(
                FunctionV1.call.call_args_list,
                [
                    call(
                        {
                            **kwargs,
                            "filename": model.media.hash,
                            "bucket": "bucket-name",
                        }
                    ),
                ],
            )

            # teardown
            self.bc.database.delete("media.MediaResolution")
            Logger.error.call_args_list = []
            FunctionV1.__init__.call_args_list = []
            FunctionV1.call.call_args_list = []

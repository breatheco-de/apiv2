"""
Test /answer
"""

from logging import Logger
from unittest.mock import MagicMock, PropertyMock, call, patch
import pytest

from rest_framework.test import APIClient
from breathecode.registry.tasks import async_create_asset_thumbnail
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    from linked_services.django.actions import reset_app_cache

    reset_app_cache()
    yield


class ResponseMock:

    def __init__(self, data, status=200, headers={}):
        self.content = data
        self.status_code = status
        self.headers = headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


fake_file_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x03\x02\x02\x02\x02\x02\x03\x02\x02\x02\x03\x03\x03\x03\x04\x06\x04\x04\x04\x04\x04\x08\x06\x06\x05\x06\t\x08\n\n\t\x08\t\t\n\x0c\x0f\x0c\n\x0b\x0e\x0b\t\t\r\x11\r\x0e\x0f\x10\x10\x11\x10\n\x0c\x12\x13\x12\x10\x13\x0f\x10\x10\x10\xff\xdb\x00C\x01\x03\x03\x03\x04\x03\x04\x08\x04\x04\x08\x10\x0b\t\x0b\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\x10\xff\xc0\x00\x11\x08\x02v\x04\xb0\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1e\x00\x01\x00\x02\x02\x03\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x06\x04\x07\x03\x08\t\x02\x01\n\xff\xc4\x00i\x10\x00\x00\x06\x01\x03\x01\x03\x04\x08\r\x11\x07\x03\x01\x00\x13\x00\x01\x02\x03\x04\x05\x06\x07\x11\x12!\x08\x13\x14\t"1A\x15\x162QT\x93\xa1\xd2\x17\x18#SVWatu\x81\x95\xb4\xd3345678BCRqv\x94\xa5\xb1\xb3\xb5\xc19b\x83\x91\xb2\xd1\xd4$rs%\x19&\x82\x92Dchw\x97\xa4\xc3\xd5\xa3\xa6\xc4\xe1\xe4\xf0\xf1\xff\xc4\x00\x1c\x01\x01\x00\x02\x03\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x04\x01\x02\x05\x06\x07\x08\xff\xc4\x00R\x11\x00\x02\x01\x02\x04\x02\x04\x08\t\x0b\x03\x02\x04\x05\x05\x01\x00\x01\x02\x03\x11\x04\x05\x12!1A\x06\x13"Q\x142aq\x81\x91\xa1\xd1\x15\x165RTs\x93\xb1\xd2#34BSr\x92\xb2\xb3\xc1\xd3\x07\xa2\xf0\x17\xe1$b\x82\xf1%Cc\xa3\xe2\x08D\x95\xc2\xd4\x83\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xf5L\x00\x00\x00\x00\x00\x00\x00~n^\xf8\x03\xf4\x00\x00\x00\x1f\x86dE\xb9\x99\x10\x03\xf7\xd2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class StreamReaderMock:

    def __init__(self, data):
        self.data = data
        self.content = data

    async def read(self):
        return self.data


@pytest.fixture(autouse=True)
def patch_get(monkeypatch):

    def handler(expected, code, headers):

        reader = StreamReaderMock(expected)
        monkeypatch.setattr("requests.request", MagicMock(return_value=ResponseMock(expected, code, headers)))

    yield handler


@patch("logging.Logger.warning", MagicMock())
@patch("logging.Logger.error", MagicMock())
def test__without_asset(bc: Breathecode, client: APIClient):
    async_create_asset_thumbnail.delay("slug")

    assert bc.database.list_of("media.Media") == []
    assert Logger.warning.call_args_list == [call("Asset with slug slug not found")]
    assert Logger.error.call_args_list == [call("Asset with slug slug not found", exc_info=True)]


@patch("logging.Logger.warning", MagicMock())
@patch("logging.Logger.error", MagicMock())
@patch(
    "os.getenv",
    MagicMock(side_effect=apply_get_env({"GOOGLE_PROJECT_ID": "labor-day-story", "SCREENSHOT_MACHINE_KEY": "000000"})),
)
def test__with_asset__bad_function_response(bc: Breathecode, client: APIClient, patch_get):
    asset_category = {"preview_generation_url": bc.fake.url()}

    model = bc.database.create_v2(asset=1, asset_category=asset_category, academy=1)

    headers = {"Accept": "*/*", "content-type": "image/jpeg"}
    patch_get(fake_file_data, 400, headers)

    async_create_asset_thumbnail.delay(model.asset.slug)

    assert bc.database.list_of("media.Media") == []
    assert Logger.warning.call_args_list == []

    assert Logger.error.call_args_list == [
        call(
            "Unhandled error with async_create_asset_thumbnail, the cloud function `screenshots` "
            "returns status code 400",
            exc_info=True,
        ),
    ]


@patch("logging.Logger.warning", MagicMock())
@patch("logging.Logger.error", MagicMock())
@patch.multiple(
    "breathecode.services.google_cloud.Storage",
    __init__=MagicMock(return_value=None),
    client=PropertyMock(),
    create=True,
)
@patch.multiple(
    "breathecode.services.google_cloud.File",
    __init__=MagicMock(return_value=None),
    bucket=PropertyMock(),
    file_name=PropertyMock(),
    delete=MagicMock(),
    download=MagicMock(return_value=bytes("qwerty", "utf-8")),
    url=MagicMock(return_value="https://uio.io/path"),
    create=True,
)
@patch(
    "os.getenv",
    MagicMock(
        side_effect=apply_get_env(
            {
                "GOOGLE_PROJECT_ID": "labor-day-story",
                "SCREENSHOTS_BUCKET": "random-bucket",
                "SCREENSHOT_MACHINE_KEY": "000000",
            }
        )
    ),
)
def test__with_asset__good_function_response(bc: Breathecode, client: APIClient, patch_get):

    hash = "3d78522863c7781e5800cd3c7dfe6450856db9eb9166f43ecfe82ccdbe95173a"
    fake_url = bc.fake.url()

    asset_category = {"preview_generation_url": fake_url}
    model = bc.database.create_v2(asset=1, asset_category=asset_category, academy=1)

    headers = {"Accept": "*/*", "content-type": "image/jpeg"}
    patch_get(fake_file_data, 200, headers)
    async_create_asset_thumbnail.delay(model.asset.slug)

    assert bc.database.list_of("media.Media") == [
        {
            "academy_id": model.asset.academy.id,
            "hash": hash,
            "hits": 0,
            "id": 1,
            "mime": "image/png",
            "name": f"{model.asset.academy.slug}-{model.asset.category.slug}-{model.asset.slug}.png",
            "slug": f"{model.asset.academy.slug}-{model.asset.category.slug}-{model.asset.slug}",
            "thumbnail": f"https://storage.googleapis.com/random-bucket/{hash}-thumbnail",
            "url": f"https://storage.googleapis.com/random-bucket/{hash}",
        }
    ]
    assert Logger.warning.call_args_list == [
        call(f"Media was save with {hash} for academy {model.asset.academy}"),
    ]
    assert Logger.error.call_args_list == []


@patch("logging.Logger.warning", MagicMock())
@patch("logging.Logger.error", MagicMock())
@patch.multiple(
    "breathecode.services.google_cloud.Storage",
    __init__=MagicMock(return_value=None),
    client=PropertyMock(),
    create=True,
)
@patch.multiple(
    "breathecode.services.google_cloud.File",
    __init__=MagicMock(return_value=None),
    delete=MagicMock(),
    download=MagicMock(return_value=bytes("qwerty", "utf-8")),
    create=True,
)
@patch(
    "os.getenv",
    MagicMock(side_effect=apply_get_env({"GOOGLE_PROJECT_ID": "labor-day-story", "SCREENSHOT_MACHINE_KEY": "000000"})),
)
def test__with_asset__with_media__without_asset_category_with_url(bc: Breathecode, client: APIClient, patch_get):
    hash = "3d78522863c7781e5800cd3c7dfe6450856db9eb9166f43ecfe82ccdbe95173a"
    media = {"hash": hash}
    model = bc.database.create_v2(asset=1, media=media)

    headers = {"Accept": "*/*", "content-type": "image/jpeg"}
    patch_get(fake_file_data, 200, headers)

    async_create_asset_thumbnail.delay(model.asset.slug)

    assert bc.database.list_of("media.Media") == [
        bc.format.to_dict(model.media),
    ]
    assert Logger.warning.call_args_list == []
    assert Logger.error.call_args_list == [
        call("Not able to retrieve a preview generation", exc_info=True),
    ]


@patch("logging.Logger.warning", MagicMock())
@patch("logging.Logger.error", MagicMock())
@patch.multiple(
    "breathecode.services.google_cloud.Storage",
    __init__=MagicMock(return_value=None),
    client=PropertyMock(),
    create=True,
)
@patch.multiple(
    "breathecode.services.google_cloud.File",
    __init__=MagicMock(return_value=None),
    bucket=PropertyMock(),
    file_name=PropertyMock(),
    delete=MagicMock(),
    rename=MagicMock(),
    download=MagicMock(return_value=bytes("qwerty", "utf-8")),
    create=True,
)
@patch(
    "os.getenv",
    MagicMock(
        side_effect=apply_get_env(
            {
                "GOOGLE_PROJECT_ID": "labor-day-story",
                "SCREENSHOT_MACHINE_KEY": "000000",
                "SCREENSHOTS_BUCKET": "random-bucket",
            }
        )
    ),
)
def test__with_asset__with_media__with_asset_category_with_url(bc: Breathecode, client: APIClient, patch_get):
    hash = "3d78522863c7781e5800cd3c7dfe6450856db9eb9166f43ecfe82ccdbe95173a"
    media = {"hash": hash}
    asset_category = {"preview_generation_url": bc.fake.url()}
    model = bc.database.create_v2(asset=1, media=media, asset_category=asset_category, academy=1)

    headers = {"Accept": "*/*", "content-type": "image/jpeg"}
    patch_get(fake_file_data, 200, headers)

    async_create_asset_thumbnail.delay(model.asset.slug)

    assert bc.database.list_of("media.Media") == [
        bc.format.to_dict(model.media),
    ]

    assert Logger.warning.call_args_list == []
    assert Logger.error.call_args_list == [
        call(f"Media with hash {hash} already exists, skipping", exc_info=True),
    ]


@patch("logging.Logger.warning", MagicMock())
@patch("logging.Logger.error", MagicMock())
@patch.multiple(
    "breathecode.services.google_cloud.Storage",
    __init__=MagicMock(return_value=None),
    client=PropertyMock(),
    create=True,
)
@patch.multiple(
    "breathecode.services.google_cloud.File",
    __init__=MagicMock(return_value=None),
    bucket=PropertyMock(),
    file_name=PropertyMock(),
    delete=MagicMock(),
    download=MagicMock(return_value=bytes("qwerty", "utf-8")),
    create=True,
)
@patch("os.getenv", MagicMock(side_effect=apply_get_env({"GOOGLE_PROJECT_ID": "labor-day-story"})))
def test__with_asset__with_media__media_for_another_academy(bc: Breathecode, client: APIClient, patch_get):
    hash = "3d78522863c7781e5800cd3c7dfe6450856db9eb9166f43ecfe82ccdbe95173a"
    asset = {"academy_id": 1}
    media = {"hash": hash, "academy_id": 2}
    asset_category = {"preview_generation_url": bc.fake.url()}
    model = bc.database.create(asset=asset, media=media, academy=2, asset_category=asset_category)

    headers = {"Accept": "*/*", "content-type": "image/jpeg"}
    patch_get(fake_file_data, 200, headers)

    async_create_asset_thumbnail.delay(model.asset.slug)

    assert bc.database.list_of("media.Media") == [
        bc.format.to_dict(model.media),
        {
            **bc.format.to_dict(model.media),
            "id": 2,
            "academy_id": 1,
            "slug": f"{model.asset.academy.slug}-{model.asset.category.slug}-{model.asset.slug}",
        },
    ]
    assert Logger.warning.call_args_list == []
    assert Logger.error.call_args_list == [
        call(f"Media was save with {hash} for academy {model.academy[0]}", exc_info=True),
    ]

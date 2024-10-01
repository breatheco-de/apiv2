"""
Test /answer
"""

from io import BytesIO
from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest

from breathecode.media import settings
from breathecode.media.settings import MEDIA_SETTINGS, process_profile
from breathecode.notify.models import Notification


@pytest.fixture(autouse=True)
def url(db, monkeypatch: pytest.MonkeyPatch, fake: capy.Fake, image: capy.Image):
    url = fake.url()
    monkeypatch.setenv("PROFILE_BUCKET", "profile-bucket")
    monkeypatch.setattr("breathecode.media.settings.save_file", MagicMock(return_value=url))
    yield url


def test_is_profile_process():
    assert MEDIA_SETTINGS["profile-picture"]["process"] is process_profile


@pytest.mark.parametrize("width, height", [(10, 20), (20, 10)])
def test_no_square_image(
    database: capy.Database,
    image: capy.Image,
    monkeypatch: pytest.MonkeyPatch,
    width: int,
    height: int,
):

    f = image.random(width, height)
    monkeypatch.setattr("breathecode.media.settings.get_file", MagicMock(return_value=f))

    model = database.create(
        file={
            "mime": "image/png",
        },
    )

    res = process_profile(model.file)

    assert res == Notification.error("Profile picture must be square")

    assert settings.get_file.call_args_list == [call(model.file)]
    assert settings.save_file.call_args_list == []
    assert database.list_of("authenticate.Profile") == []


def test_no_profile(
    database: capy.Database, url: str, fake: capy.Fake, image: capy.Image, monkeypatch: pytest.MonkeyPatch
):

    f = image.random(10, 10)
    monkeypatch.setattr("breathecode.media.settings.get_file", MagicMock(return_value=f))

    model = database.create(
        file={
            "mime": "image/png",
        },
    )

    res = process_profile(model.file)

    assert res == Notification.info("Profile picture was updated")

    assert settings.get_file.call_args_list == [call(model.file)]
    assert settings.save_file.call_count == 1
    for x in settings.save_file.call_args_list:
        # because the file was closed we can't assert its content
        assert call(type(x[0][0]), *x[0][1:], **x[1]) == call(
            BytesIO, "profile-bucket", f"{model.file.file_name}-120x120", "image/png"
        )

    assert database.list_of("authenticate.Profile") == [
        {
            "avatar_url": url,
            "bio": None,
            "blog": None,
            "github_username": None,
            "id": 1,
            "linkedin_url": None,
            "phone": "",
            "portfolio_url": None,
            "show_tutorial": True,
            "twitter_username": None,
            "user_id": 1,
        },
    ]


def test_with_profile__different_image(
    database: capy.Database, url: str, format: capy.Format, image: capy.Image, monkeypatch: pytest.MonkeyPatch
):

    f = image.random(10, 10)
    monkeypatch.setattr("breathecode.media.settings.get_file", MagicMock(return_value=f))

    model = database.create(
        file={
            "mime": "image/png",
        },
        user=1,
        profile=1,
    )

    res = process_profile(model.file)

    assert res == Notification.info("Profile picture was updated")

    assert settings.get_file.call_args_list == [call(model.file)]
    assert settings.save_file.call_count == 1
    for x in settings.save_file.call_args_list:
        # because the file was closed we can't assert its content
        assert call(type(x[0][0]), *x[0][1:], **x[1]) == call(
            BytesIO, "profile-bucket", f"{model.file.file_name}-120x120", "image/png"
        )

    assert database.list_of("authenticate.Profile") == [
        {
            **format.to_obj_repr(model.profile),
            "avatar_url": url,
        },
    ]


def test_with_profile__same_image(
    database: capy.Database, url: str, format: capy.Format, image: capy.Image, monkeypatch: pytest.MonkeyPatch
):

    f = image.random(10, 10)
    monkeypatch.setattr("breathecode.media.settings.get_file", MagicMock(return_value=f))

    model = database.create(
        file={
            "mime": "image/png",
        },
        user=1,
        profile={
            "avatar_url": url,
        },
    )

    res = process_profile(model.file)

    assert res == Notification.info("You uploaded the same profile picture")

    assert settings.get_file.call_args_list == [call(model.file)]
    assert settings.save_file.call_count == 1
    for x in settings.save_file.call_args_list:
        # because the file was closed we can't assert its content
        assert call(type(x[0][0]), *x[0][1:], **x[1]) == call(
            BytesIO, "profile-bucket", f"{model.file.file_name}-120x120", "image/png"
        )

    assert database.list_of("authenticate.Profile") == [
        format.to_obj_repr(model.profile),
    ]

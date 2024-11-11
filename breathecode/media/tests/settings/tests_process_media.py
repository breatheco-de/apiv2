"""
Test /answer
"""

from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest

from breathecode.media import settings
from breathecode.media.settings import MEDIA_SETTINGS, process_media
from breathecode.notify.models import Notification


@pytest.fixture(autouse=True)
def url(db, monkeypatch: pytest.MonkeyPatch, fake: capy.Fake):
    url = fake.url()
    monkeypatch.setattr("breathecode.media.settings.transfer", MagicMock(return_value=url))
    monkeypatch.setattr("breathecode.media.settings.del_temp_file", MagicMock(return_value=url))
    monkeypatch.setenv("MEDIA_GALLERY_BUCKET", "galery-bucket")
    yield url


def test_is_media_process():
    assert MEDIA_SETTINGS["media"]["process"] is process_media


def test_no_media(database: capy.Database, url: str, fake: capy.Fake):
    meta = {
        "slug": fake.slug(),
        "name": fake.name(),
    }
    categories = [{"slug": fake.slug()} for _ in range(2)]
    model = database.create(
        file={
            "meta": {
                **meta,
                "categories": [x["slug"] for x in categories],
            }
        },
        academy=2,
        city=1,
        country=1,
    )

    res = process_media(model.file)

    assert res == Notification.info("Media processed")
    assert settings.transfer.call_args_list == [call(model.file, "galery-bucket")]
    assert settings.del_temp_file.call_args_list == []
    assert database.list_of("media.Media") == [
        {
            "academy_id": 1,
            "hash": model.file.hash,
            "hits": 0,
            "id": 1,
            "mime": model.file.mime,
            "thumbnail": url + "-thumbnail",
            "url": url,
            **meta,
        },
    ]


def test_media__same_academy(database: capy.Database, format: capy.Format, queryset: capy.QuerySet, fake: capy.Fake):
    hash = fake.md5()
    categories = [{"slug": fake.slug()} for _ in range(2)]
    model = database.create(
        file={
            "meta": {
                "slug": fake.slug(),
                "name": fake.name(),
                "categories": [x["slug"] for x in categories],
            },
            "hash": hash,
        },
        academy=1,
        city=1,
        country=1,
        media={
            "hash": hash,
            "categories": [1, 2],
        },
        category=categories,
    )

    res = process_media(model.file)

    assert res == Notification.info("Media already exists")
    assert settings.transfer.call_args_list == []
    assert settings.del_temp_file.call_args_list == [call(model.file)]
    assert database.list_of("media.Media") == [format.to_obj_repr(model.media)]

    assert queryset.get_pks(model.media.categories.all()) == [1, 2]


def test_media__other_academy(database: capy.Database, format: capy.Format, queryset: capy.QuerySet, fake: capy.Fake):
    meta = {
        "slug": fake.slug(),
        "name": fake.name(),
    }
    categories = [{"slug": fake.slug()} for _ in range(2)]
    hash = fake.md5()
    model = database.create(
        file={
            "meta": {
                **meta,
                "categories": [x["slug"] for x in categories],
            },
            "hash": hash,
        },
        academy=2,
        city=1,
        country=1,
        media={
            "hash": hash,
            "academy_id": 2,
        },
        category=categories,
    )

    res = process_media(model.file)

    assert res == Notification.info("Media processed")
    assert settings.transfer.call_args_list == []
    assert settings.del_temp_file.call_args_list == [call(model.file)]
    assert database.list_of("media.Media") == [
        format.to_obj_repr(model.media),
        {
            "academy_id": 1,
            "hash": model.file.hash,
            "hits": 0,
            "id": 2,
            "mime": model.file.mime,
            "thumbnail": model.media.url + "-thumbnail",
            "url": model.media.url,
            **meta,
        },
    ]

    Media = database.get_model("media.Media")
    media = Media.objects.filter(id=2).first()

    assert queryset.get_pks(media.categories.all()) == [1, 2]

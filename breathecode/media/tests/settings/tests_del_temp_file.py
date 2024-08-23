"""
Test /answer
"""

from unittest.mock import MagicMock, PropertyMock, call

import pytest

from breathecode.media.settings import del_temp_file
from breathecode.services.google_cloud import File, Storage
from capyc.rest_framework import pytest as capy


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.__init__", MagicMock(return_value=None))
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.client", PropertyMock(), raising=False)
    monkeypatch.setattr("breathecode.services.google_cloud.File.delete", MagicMock())


def test_file_does_not_exists(monkeypatch: pytest.MonkeyPatch, database: capy.Database, fake: capy.Fake):
    monkeypatch.setattr("breathecode.services.google_cloud.File.exists", MagicMock(return_value=False))

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

    with pytest.raises(Exception, match="File does not exists"):
        del_temp_file(model.file)

    assert Storage.__init__.call_args_list == [call()]
    assert File.exists.call_args_list == [call()]
    assert File.delete.call_args_list == []


def test_file_exists(monkeypatch: pytest.MonkeyPatch, database: capy.Database, fake: capy.Fake):
    monkeypatch.setattr("breathecode.services.google_cloud.File.exists", MagicMock(return_value=True))

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

    del_temp_file(model.file)

    assert Storage.__init__.call_args_list == [call()]
    assert File.exists.call_args_list == [call()]
    assert File.delete.call_args_list == [call()]

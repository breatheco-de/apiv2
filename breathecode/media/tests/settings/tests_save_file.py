"""
Test /answer
"""

from io import BytesIO
from unittest.mock import MagicMock, PropertyMock, call

import capyc.pytest as capy
import pytest

from breathecode.media.settings import save_file
from breathecode.services.google_cloud import File, Storage


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    def download(f: BytesIO):
        f.write(b"123")
        f.seek(0)

    monkeypatch.setattr("breathecode.services.google_cloud.Storage.__init__", MagicMock(return_value=None))
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.client", PropertyMock(), raising=False)
    monkeypatch.setattr("breathecode.services.google_cloud.File.upload", MagicMock())
    monkeypatch.setattr("breathecode.services.google_cloud.File.url", MagicMock(return_value="123456"))


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

    f = BytesIO()
    res = save_file(f, "my-bucket", "my-file", "image/png")

    assert res == "123456"
    assert Storage.__init__.call_args_list == [call()]
    assert File.exists.call_args_list == [call()]
    assert File.upload.call_args_list == [call(f, content_type="image/png")]


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

    f = BytesIO()
    res = save_file(f, "my-bucket", "my-file", "image/png")

    assert res == "123456"
    assert Storage.__init__.call_args_list == [call()]
    assert File.exists.call_args_list == [call()]
    assert File.upload.call_args_list == []

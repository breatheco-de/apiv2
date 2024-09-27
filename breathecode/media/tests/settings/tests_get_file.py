"""
Test /answer
"""

from io import BytesIO
from unittest.mock import MagicMock, PropertyMock, call

import capyc.pytest as capy
import pytest

from breathecode.media.settings import get_file
from breathecode.services.google_cloud import File, Storage


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    def download(f: BytesIO):
        f.write(b"123")
        f.seek(0)

    monkeypatch.setattr("breathecode.services.google_cloud.Storage.__init__", MagicMock(return_value=None))
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.client", PropertyMock(), raising=False)
    monkeypatch.setattr("breathecode.services.google_cloud.File.download", MagicMock(side_effect=download))


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
        get_file(model.file)

    assert Storage.__init__.call_args_list == [call()]
    assert File.exists.call_args_list == [call()]
    assert File.download.call_args_list == []


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

    res = get_file(model.file)

    assert res.read() == b"123"
    assert Storage.__init__.call_args_list == [call()]
    assert File.exists.call_args_list == [call()]
    assert File.download.call_count == 1

    for x in File.download.call_args_list:
        assert call(type(x[0][0]), *[0][1:], **x[1]) == call(BytesIO)

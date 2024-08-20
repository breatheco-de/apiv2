"""
Test /answer
"""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, PropertyMock, call

import pytest

from breathecode.media import settings
from breathecode.media.settings import MEDIA_SETTINGS, transfer
from breathecode.services.google_cloud import File, Storage
from capyc.rest_framework import pytest as capy


def mock_download(x: BytesIO) -> None:
    x.write(b"my_line\n")


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.__init__", MagicMock(return_value=None))
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.client", PropertyMock(), raising=False)
    monkeypatch.setattr("breathecode.services.google_cloud.File.download", MagicMock(side_effect=mock_download))
    monkeypatch.setattr("breathecode.services.google_cloud.File.upload", MagicMock())
    monkeypatch.setattr("breathecode.services.google_cloud.File.delete", MagicMock())
    monkeypatch.setattr("breathecode.media.signals.schedule_deletion.adelay", AsyncMock())
    monkeypatch.setattr("breathecode.media.tasks.process_file.delay", AsyncMock())


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
        transfer(model.file, "my-bucket")

    assert Storage.__init__.call_args_list == [call()]
    assert File.exists.call_args_list == [call()]
    assert File.delete.call_args_list == []
    assert File.download.call_args_list == []
    assert File.upload.call_args_list == []


def test_file_exists(monkeypatch: pytest.MonkeyPatch, database: capy.Database, fake: capy.Fake):
    file_init_mock = MagicMock(return_value=None)
    c = File.__init__
    url = fake.url()

    def wrapper(self, *args, **kwargs):
        c(self, *args, **kwargs)
        file_init_mock(*args, **kwargs)

    monkeypatch.setattr("breathecode.services.google_cloud.File.exists", MagicMock(return_value=True))
    monkeypatch.setattr("breathecode.services.google_cloud.File.__init__", wrapper)
    monkeypatch.setattr("breathecode.services.google_cloud.File.url", MagicMock(return_value=url))

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

    res = transfer(model.file, "my-bucket")

    assert res == url

    assert Storage.__init__.call_args_list == [call()]
    assert [call(*args[1:], **kwargs) for args, kwargs in file_init_mock.call_args_list] == [
        call(model.file.hash),
        call(model.file.hash),
    ]

    assert File.exists.call_args_list == [call()]

    assert [call(args[0].getvalue(), *args[1:], **kwargs) for args, kwargs in File.download.call_args_list] == [
        call(BytesIO(b"my_line\n").getvalue()),
    ]

    assert File.upload.call_args_list == [call(File.download.call_args_list[0][0][0], content_type=model.file.mime)]

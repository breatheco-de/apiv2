"""
Test /answer
"""

import random
from unittest.mock import MagicMock, PropertyMock, call

import pytest

from breathecode.media import settings
from breathecode.media.signals import schedule_deletion
from breathecode.services.google_cloud import File, Storage
from capyc.rest_framework import pytest as capy


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.media.settings.del_temp_file", MagicMock())


def test_unique_chunk_instance(
    monkeypatch: pytest.MonkeyPatch, database: capy.Database, fake: capy.Fake, signals: capy.Signals
):
    monkeypatch.setattr("breathecode.services.google_cloud.File.exists", MagicMock(return_value=False))
    signals.enable("breathecode.media.signals.schedule_deletion")

    model = database.create(
        chunk=1,
        academy=2,
        city=1,
        country=1,
    )

    schedule_deletion.send(instance=model.chunk, sender=model.chunk.__class__)

    assert settings.del_temp_file.call_args_list == [call(model.chunk)]
    assert database.list_of("media.Chunk") == []


def test_duplicated_chunk_instance(
    monkeypatch: pytest.MonkeyPatch,
    database: capy.Database,
    fake: capy.Fake,
    signals: capy.Signals,
    format: capy.Format,
):
    monkeypatch.setattr("breathecode.services.google_cloud.File.exists", MagicMock(return_value=False))
    signals.enable("breathecode.media.signals.schedule_deletion")

    model = database.create(
        chunk=(
            2,
            {
                "name": fake.name(),
                "mime": fake.name(),
                "total_chunks": random.randint(1, 10),
            },
        ),
        academy=2,
        city=1,
        country=1,
    )

    schedule_deletion.send(instance=model.chunk[0], sender=model.chunk[0].__class__)

    assert settings.del_temp_file.call_args_list == []
    assert database.list_of("media.Chunk") == [format.to_obj_repr(model.chunk[1])]

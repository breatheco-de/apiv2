"""
Test /answer
"""

from logging import Logger
from typing import Any
from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest

from breathecode.media.settings import MEDIA_SETTINGS
from breathecode.media.tasks import process_file
from breathecode.notify.models import Notification


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("logging.Logger.warning", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("breathecode.notify.models.Notification.send", MagicMock(wraps=Notification.send))


def test_no_file():
    process_file.delay(1)

    assert Logger.warning.call_args_list == [call("File with id 1 not found")]
    assert Logger.error.call_args_list == [call("File with id 1 not found", exc_info=True)]
    assert Notification.send.call_args_list == []


@pytest.mark.parametrize("extra", [{}, {"academy": 1, "city": 1, "country": 1}])
def test_bad_op_type(database: capy.Database, extra: dict):
    model = database.create(file={"status": "TRANSFERRING"}, **extra)

    process_file.delay(1)

    assert Logger.warning.call_args_list == []
    assert Logger.error.call_args_list == [
        call(f"No settings found for operation type {model.file.operation_type}", exc_info=True)
    ]
    assert Notification.send.call_args_list == []


@pytest.mark.parametrize("extra", [{}, {"academy": 1, "city": 1, "country": 1}])
def test_no_process_fn(database: capy.Database, extra: dict):
    model = database.create(file={"status": "TRANSFERRING", "operation_type": "proof-of-payment"}, **extra)

    process_file.delay(1)

    assert Logger.warning.call_args_list == []
    assert Logger.error.call_args_list == [call("Invalid process for operation type proof-of-payment", exc_info=True)]
    assert Notification.send.call_args_list == []


@pytest.mark.parametrize("extra", [{}, {"academy": 1, "city": 1, "country": 1}])
@pytest.mark.parametrize("op_type", ["media", "profile-picture"])
def test_process_file(database: capy.Database, extra: dict, op_type: str, monkeypatch: pytest.MonkeyPatch):
    m = MagicMock()
    monkeypatch.setitem(MEDIA_SETTINGS[op_type], "process", m)

    model = database.create(file={"status": "TRANSFERRING", "operation_type": op_type}, **extra)

    process_file.delay(1)

    assert Logger.warning.call_args_list == []
    assert Logger.error.call_args_list == []
    assert m.call_args_list == [call(model.file)]
    assert Notification.send.call_args_list == []


@pytest.mark.parametrize("op_type", ["media", "profile-picture"])
def test_process_file__notification_not_found(database: capy.Database, op_type: str, monkeypatch: pytest.MonkeyPatch):
    m = MagicMock()
    monkeypatch.setitem(MEDIA_SETTINGS[op_type], "process", m)

    model = database.create(file={"status": "TRANSFERRING", "operation_type": op_type}, academy=1, city=1, country=1)

    process_file.delay(1, 1)

    assert Logger.warning.call_args_list == []
    assert Logger.error.call_args_list == []
    assert m.call_args_list == [call(model.file)]
    assert Notification.send.call_args_list == []


@pytest.mark.parametrize("op_type", ["media", "profile-picture"])
@pytest.mark.parametrize(
    "msg", [Notification.error("test1"), Notification.warning("test2"), Notification.info("test3")]
)
def test_process_file__send_notification(
    database: capy.Database, op_type: str, monkeypatch: pytest.MonkeyPatch, msg: Any
):
    m = MagicMock(return_value=msg)
    monkeypatch.setitem(MEDIA_SETTINGS[op_type], "process", m)

    model = database.create(
        file={"status": "TRANSFERRING", "operation_type": op_type},
        academy=1,
        city=1,
        country=1,
        notification=1,
    )

    process_file.delay(1, 1)

    assert Logger.warning.call_args_list == []
    assert Logger.error.call_args_list == []
    assert m.call_args_list == [call(model.file)]
    assert Notification.send.call_args_list == [call(msg, model.notification)]

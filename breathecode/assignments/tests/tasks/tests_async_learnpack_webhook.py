"""
Test /answer
"""

from logging import Logger
from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest
from linked_services.django.actions import reset_app_cache

from breathecode.services.learnpack.client import LearnPack

from ...tasks import async_learnpack_webhook


@pytest.fixture(autouse=True)
def x(db: None, monkeypatch: pytest.MonkeyPatch):
    reset_app_cache()

    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())

    yield


@pytest.fixture
def successful_webhook(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.services.learnpack.client.LearnPack.execute_action", MagicMock())


@pytest.fixture
def failed_webhook(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "breathecode.services.learnpack.client.LearnPack.execute_action", MagicMock(side_effect=Exception("Error"))
    )


def test_no_webhook(database: capy.Database, successful_webhook: None):
    async_learnpack_webhook.delay(1)

    assert Logger.info.call_args_list == [
        call("Starting async_learnpack_webhook for webhook 1"),
        call("Starting async_learnpack_webhook for webhook 1"),
    ]
    assert Logger.error.call_args_list == [
        call("Webhook 1 not found", exc_info=True),
    ]
    assert database.list_of("assignments.LearnPackWebhook") == []
    assert LearnPack.execute_action.call_args_list == []


def test_trigger_webhook(database: capy.Database, format: capy.Format, successful_webhook: None):
    model = database.create(learn_pack_webhook=1)
    Logger.info.reset_mock()
    async_learnpack_webhook.delay(1)

    assert Logger.info.call_args_list == [
        call("Starting async_learnpack_webhook for webhook 1"),
    ]
    assert Logger.error.call_args_list == []
    assert database.list_of("assignments.LearnPackWebhook") == [format.to_obj_repr(model.learn_pack_webhook)]
    assert LearnPack.execute_action.call_args_list == [call(1)]


def test_trigger_webhook_with_error(database: capy.Database, format: capy.Format, failed_webhook: None):
    model = database.create(learn_pack_webhook=1)
    Logger.info.reset_mock()
    async_learnpack_webhook.delay(1)

    assert Logger.info.call_args_list == [
        call("Starting async_learnpack_webhook for webhook 1"),
    ]
    assert Logger.error.call_args_list == [
        call("Error", exc_info=True),
    ]
    assert database.list_of("assignments.LearnPackWebhook") == [
        {
            **format.to_obj_repr(model.learn_pack_webhook),
            "status": "ERROR",
            "status_text": "Error",
        }
    ]
    assert LearnPack.execute_action.call_args_list == [call(1)]

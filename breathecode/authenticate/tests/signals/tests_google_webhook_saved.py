from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest

from breathecode.notify import tasks
from breathecode.payments.tasks import process_google_webhook
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr("breathecode.payments.tasks.process_google_webhook.delay", MagicMock())
    yield


def test_each_webhook_is_processed(database: capy.Database, signals: capy.Signals, format: capy.Format):
    signals.enable("breathecode.authenticate.signals.google_webhook_saved")

    model = database.create(
        google_webhook=2,
    )

    assert database.list_of("authenticate.GoogleWebhook") == [
        format.to_obj_repr(model.google_webhook[0]),
        format.to_obj_repr(model.google_webhook[1]),
    ]

    assert process_google_webhook.delay.call_args_list == [
        call(1),
        call(2),
    ]

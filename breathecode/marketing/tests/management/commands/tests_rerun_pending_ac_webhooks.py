from datetime import timedelta
from unittest.mock import MagicMock, call

import pytest
from django.utils import timezone

import breathecode.marketing.tasks as tasks
from breathecode.marketing.management.commands.rerun_pending_ac_webhooks import Command
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr(tasks.async_activecampaign_webhook, "delay", MagicMock())
    yield


def test_no_webhooks():
    command = Command()
    command.handle()

    assert tasks.async_activecampaign_webhook.delay.call_args_list == []


def generate_params():
    deltas = [timedelta(days=0), timedelta(days=1), timedelta(days=2)]
    for delta in deltas:
        yield "PENDING", delta

    deltas = deltas + [None, timedelta(days=3, seconds=1), timedelta(days=4), timedelta(days=5)]
    for status in ["DONE", "ERROR"]:
        for delta in deltas:
            yield status, delta


@pytest.mark.parametrize("status,delta", [*generate_params()])
def test_with_webhooks_requirements_no_meet(bc: Breathecode, status, delta):
    active_campaign_webhook = {
        "status": status,
        "payload": {},
        "run_at": None,
    }
    if delta is not None:
        active_campaign_webhook["run_at"] = timezone.now() - delta

    model = bc.database.create(active_campaign_webhook=active_campaign_webhook)
    command = Command()
    command.handle()

    assert bc.database.list_of("marketing.ActiveCampaignWebhook") == [
        bc.format.to_dict(model.active_campaign_webhook),
    ]
    assert tasks.async_activecampaign_webhook.delay.call_args_list == []


def generate_params():
    deltas = [None, timedelta(days=3, seconds=1), timedelta(days=4), timedelta(days=5)]
    for delta in deltas:
        yield "PENDING", delta


@pytest.mark.parametrize("status,delta", [*generate_params()])
def test_with_webhooks_requirements_meet(bc: Breathecode, status, delta):
    active_campaign_webhook = {
        "status": status,
        "payload": {},
        "run_at": None,
    }
    if delta is not None:
        active_campaign_webhook["run_at"] = timezone.now() - delta

    model = bc.database.create(active_campaign_webhook=(3, active_campaign_webhook))
    command = Command()
    command.handle()

    assert bc.database.list_of("marketing.ActiveCampaignWebhook") == bc.format.to_dict(model.active_campaign_webhook)

    assert tasks.async_activecampaign_webhook.delay.call_args_list == [call(n + 1) for n in range(3)]

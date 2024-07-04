from unittest.mock import MagicMock, call

import pytest

from breathecode.payments import tasks
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def mocks(db, monkeypatch):
    m1 = MagicMock()
    m2 = MagicMock()
    monkeypatch.setattr(tasks.update_subscription_service_stock_schedulers, "delay", m1)
    monkeypatch.setattr(tasks.update_plan_financing_service_stock_schedulers, "delay", m2)
    yield m1, m2


def test_nothing_happens(bc: Breathecode, mocks):

    subscription_mock, plan_financing_mock = mocks

    plan = {
        "time_of_life": 1,
        "time_of_life_unit": "MONTH",
        "trial_duration": 0,
    }

    model = bc.database.create(plan=plan)
    tasks.update_service_stock_schedulers.delay(1)

    assert subscription_mock.call_args_list == []
    assert plan_financing_mock.call_args_list == []


def test_calling_the_builders_for_the_related_content(bc: Breathecode, mocks):

    subscription_mock, plan_financing_mock = mocks

    plan = {
        "time_of_life": 1,
        "time_of_life_unit": "MONTH",
        "trial_duration": 0,
    }

    plan_financing = {
        "plan_expires_at": bc.datetime.now(),
        "monthly_price": 10,
    }

    subscriptions = [{"plans": [1]} for x in range(1, 3)]
    subscriptions += [{"plans": []} for x in range(1, 3)]

    plan_financing = [
        {
            "plans": [1],
            "plan_expires_at": bc.datetime.now(),
            "monthly_price": 10,
        }
        for x in range(1, 3)
    ]
    plan_financing += [
        {
            "plans": [],
            "plan_expires_at": bc.datetime.now(),
            "monthly_price": 10,
        }
        for x in range(1, 3)
    ]

    model = bc.database.create(plan=plan, subscription=subscriptions, plan_financing=plan_financing)
    tasks.update_service_stock_schedulers.delay(1)

    assert subscription_mock.call_args_list == [call(1, 1), call(1, 2)]
    assert plan_financing_mock.call_args_list == [call(1, 1), call(1, 2)]

from unittest.mock import MagicMock, call

import pytest

from breathecode.payments import tasks
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

# update_plan_m2m_service_items


@pytest.fixture(autouse=True)
def mocks(db, monkeypatch):
    m1 = MagicMock()
    monkeypatch.setattr(tasks.update_service_stock_schedulers, "delay", m1)
    yield m1


@pytest.mark.parametrize(
    "plan,empty,service_item",
    [
        (None, True, None),
        (
            (
                2,
                {
                    "time_of_life": 1,
                    "time_of_life_unit": "MONTH",
                    "trial_duration": 0,
                },
            ),
            False,
            2,
        ),
    ],
)
def test_nothing_happens(bc: Breathecode, enable_signals, mocks, plan, empty, service_item):
    enable_signals("django.db.models.signals.m2m_changed", "breathecode.payments.signals.update_plan_m2m_service_items")

    mock = mocks
    model = bc.database.create(plan=plan, service_item=service_item)

    if empty:
        assert bc.database.list_of("payments.Plan") == []

    else:
        assert bc.database.list_of("payments.Plan") == bc.format.to_dict(model.plan)

    assert mock.call_args_list == []


@pytest.mark.parametrize(
    "attr,value ",
    [
        ("subscription", {}),
        (
            "plan_financing",
            {
                "monthly_price": 10,
            },
        ),
    ],
)
def test__consumable_how_many_minus_1__consume_gte_1(bc: Breathecode, enable_signals, mocks, attr, value):
    enable_signals("django.db.models.signals.m2m_changed", "breathecode.payments.signals.update_plan_m2m_service_items")

    extra = {}
    if attr == "plan_financing":
        value["plan_expires_at"] = bc.datetime.now()
        extra["plan_financing"] = (2, value)

    else:
        extra["subscription"] = (2, value)

    mock = mocks

    plan = {
        "time_of_life": 1,
        "time_of_life_unit": "MONTH",
        "trial_duration": 0,
    }

    model = bc.database.create(plan=(2, plan), service_item=2, **extra)

    for plan in model.plan:
        plan.service_items.add(*model.service_item)

    assert bc.database.list_of("payments.Plan") == bc.format.to_dict(model.plan)
    assert mock.call_args_list == [call(1), call(2)]

    assert [x.id for x in model.plan[0].service_items.all()] == [1, 2]
    assert [x.id for x in model.plan[1].service_items.all()] == [1, 2]

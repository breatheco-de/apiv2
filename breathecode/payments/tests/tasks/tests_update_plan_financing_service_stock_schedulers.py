from unittest.mock import MagicMock, call

import pytest

from breathecode.payments import tasks
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    yield


def test_nothing_happens(bc: Breathecode):
    plan = {
        "time_of_life": 1,
        "time_of_life_unit": "MONTH",
        "trial_duration": 0,
    }

    plan_financing = {
        "monthly_price": 10,
        "plan_expires_at": bc.datetime.now(),
    }

    model = bc.database.create(plan=plan, plan_financing=plan_financing)
    tasks.update_plan_financing_service_stock_schedulers.delay(1, 1)

    assert bc.database.list_of("payments.ServiceStockScheduler") == []
    assert bc.database.list_of("payments.PlanServiceItemHandler") == []


def test_all_schedulers_must_be_created(bc: Breathecode):
    plan = {
        "time_of_life": 1,
        "time_of_life_unit": "MONTH",
        "trial_duration": 0,
    }

    plan_financing = {
        "monthly_price": 10,
        "plan_expires_at": bc.datetime.now(),
    }

    plan_service_items = [
        {
            "plan_id": 1,
            "service_item_id": n,
        }
        for n in range(1, 3)
    ]

    model = bc.database.create(
        plan=plan, plan_financing=plan_financing, service_item=2, plan_service_item=plan_service_items
    )
    tasks.update_plan_financing_service_stock_schedulers.delay(1, 1)

    assert bc.database.list_of("payments.ServiceStockScheduler") == [
        {
            "id": 1,
            "plan_handler_id": 1,
            "subscription_handler_id": None,
            "valid_until": None,
        },
        {
            "id": 2,
            "plan_handler_id": 2,
            "subscription_handler_id": None,
            "valid_until": None,
        },
    ]
    assert bc.database.list_of("payments.PlanServiceItem") == [
        {
            "id": n,
            "plan_id": 1,
            "service_item_id": n,
        }
        for n in range(1, 3)
    ]
    assert bc.database.list_of("payments.PlanServiceItemHandler") == [
        {
            "handler_id": 1,
            "id": 1,
            "plan_financing_id": 1,
            "subscription_id": None,
        },
        {
            "handler_id": 2,
            "id": 2,
            "plan_financing_id": 1,
            "subscription_id": None,
        },
    ]


def test_half_schedulers_must_be_created(bc: Breathecode):
    plan = {
        "time_of_life": 1,
        "time_of_life_unit": "MONTH",
        "trial_duration": 0,
    }

    plan_financing = {
        "monthly_price": 10,
        "plan_expires_at": bc.datetime.now(),
    }

    plan_service_items = [
        {
            "plan_id": 1,
            "service_item_id": n,
        }
        for n in range(1, 5)
    ]

    service_stock_schedulers = [
        {
            "plan_handler_id": n,
            "valid_until": None,
        }
        for n in range(1, 3)
    ]

    plan_service_item_handlers = [
        {
            "handler_id": n,
            "plan_financing_id": 1,
        }
        for n in range(1, 3)
    ]

    model = bc.database.create(
        plan=plan,
        plan_financing=plan_financing,
        service_item=4,
        plan_service_item=plan_service_items,
        service_stock_scheduler=service_stock_schedulers,
        plan_service_item_handler=plan_service_item_handlers,
    )
    tasks.update_plan_financing_service_stock_schedulers.delay(1, 1)

    assert bc.database.list_of("payments.ServiceStockScheduler") == [
        {
            "id": n,
            "plan_handler_id": n,
            "subscription_handler_id": None,
            "valid_until": None,
        }
        for n in range(1, 5)
    ]
    assert bc.database.list_of("payments.PlanServiceItem") == [
        {
            "id": n,
            "plan_id": 1,
            "service_item_id": n,
        }
        for n in range(1, 5)
    ]
    assert bc.database.list_of("payments.PlanServiceItemHandler") == [
        {
            "handler_id": n,
            "id": n,
            "plan_financing_id": 1,
            "subscription_id": None,
        }
        for n in range(1, 5)
    ]

"""
Test /answer
"""

import logging
import random
from unittest.mock import MagicMock, call

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

from ...tasks import renew_consumables

UTC_NOW = timezone.now()


def consumable_item(data={}):
    return {
        "cohort_set_id": None,
        "event_type_set_id": None,
        "how_many": -1,
        "id": 0,
        "mentorship_service_set_id": None,
        "service_item_id": 0,
        "unit_type": "UNIT",
        "user_id": 0,
        "valid_until": UTC_NOW,
        "sort_priority": 1,
        **data,
    }


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    yield


def test_scheduler_not_found(bc: Breathecode):
    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
        # retrying
        call("Starting renew_consumables for service stock scheduler 1"),
    ]
    assert logging.Logger.error.call_args_list == [
        call("ServiceStockScheduler with id 1 not found", exc_info=True),
    ]

    assert bc.database.list_of("payments.Consumable") == []


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item",
    [
        ("plan_financing", True, False),
        ("subscription", False, True),
        ("subscription", True, False),
    ],
)
def test_is_over(bc: Breathecode, type: str, plan_service_item_handler: bool, subscription_service_item: bool):
    extra = {
        type: {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW - relativedelta(seconds=1),
        }
    }

    if plan_service_item_handler:
        extra["plan_service_item_handler"] = 1

    if subscription_service_item:
        extra["subscription_service_item"] = 1

    plan = {"is_renewable": False}

    model = bc.database.create(service_stock_scheduler=1, plan=plan, **extra)

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
    ]
    assert logging.Logger.error.call_args_list == [
        call(f"The {type.replace('_', ' ')} 1 is over", exc_info=True),
    ]

    assert bc.database.list_of("payments.Consumable") == []


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item",
    [
        ("plan_financing", True, False),
        ("subscription", False, True),
        ("subscription", True, False),
    ],
)
def test_plan_financing_without_be_paid(
    bc: Breathecode, type: str, plan_service_item_handler: bool, subscription_service_item: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=3),
            "valid_until": UTC_NOW - relativedelta(seconds=1),
        }

    if type == "subscription":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
        }

    if plan_service_item_handler:
        extra["plan_service_item_handler"] = 1

    if subscription_service_item:
        extra["subscription_service_item"] = 1

    plan = {"is_renewable": False}

    model = bc.database.create(service_stock_scheduler=1, plan=plan, **extra)

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
    ]
    assert logging.Logger.error.call_args_list == [
        call(f"The {type.replace('_', ' ')} 1 needs to be paid to renew the consumables", exc_info=True),
    ]

    assert bc.database.list_of("payments.Consumable") == []


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item",
    [
        ("plan_financing", True, False),
        ("subscription", False, True),
        ("subscription", True, False),
    ],
)
def test_without_a_resource_linked(
    bc: Breathecode, type: str, plan_service_item_handler: bool, subscription_service_item: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=3),
            "valid_until": UTC_NOW - relativedelta(seconds=1),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if type == "subscription":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if plan_service_item_handler:
        extra["plan_service_item_handler"] = 1

    if subscription_service_item:
        extra["subscription_service_item"] = 1

    plan = {"is_renewable": False}

    model = bc.database.create(service_stock_scheduler=1, plan=plan, **extra)

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
    ]
    assert logging.Logger.error.call_args_list == [
        call("The Plan not have a resource linked to it for the ServiceStockScheduler 1"),
    ]

    assert bc.database.list_of("payments.Consumable") == []


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item",
    [
        ("plan_financing", True, False),
        ("subscription", False, True),
        ("subscription", True, False),
    ],
)
def test_with_two_cohorts_linked(
    bc: Breathecode, type: str, plan_service_item_handler: bool, subscription_service_item: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if type == "subscription":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=2),
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if plan_service_item_handler:
        extra["plan_service_item_handler"] = 1

    if subscription_service_item:
        extra["subscription_service_item"] = 1

    plan = {"is_renewable": False}
    service_item = {"how_many": -1}
    if random.randint(0, 1) == 1:
        service_item["how_many"] = random.randint(1, 100)
    academy = {"available_as_saas": True}

    model = bc.database.create(
        service_stock_scheduler=1,
        plan=plan,
        service_item=service_item,
        cohort=2,
        cohort_set=2,
        academy=academy,
        **extra,
    )

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
        call("The consumable 1 for cohort set 1 was built"),
        call("The scheduler 1 was renewed"),
    ]
    assert logging.Logger.error.call_args_list == []

    assert bc.database.list_of("payments.Consumable") == [
        consumable_item(
            {
                "cohort_set_id": 1,
                "id": 1,
                "service_item_id": 1,
                "user_id": 1,
                "how_many": model.service_item.how_many,
                "valid_until": UTC_NOW
                + (relativedelta(minutes=5) if type == "plan_financing" else relativedelta(minutes=3)),
            }
        ),
    ]


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item",
    [
        ("plan_financing", True, False),
        ("subscription", False, True),
        ("subscription", True, False),
    ],
)
def test_two_mentorship_services_linked(
    bc: Breathecode, type: str, plan_service_item_handler: bool, subscription_service_item: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if type == "subscription":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=4),
            "valid_until": UTC_NOW + relativedelta(minutes=5),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if plan_service_item_handler:
        extra["plan_service_item_handler"] = 1

    if subscription_service_item:
        extra["subscription_service_item"] = 1

    service = {"type": "MENTORSHIP_SERVICE_SET"}
    plan = {"is_renewable": False}
    service_item = {"how_many": -1}
    if random.randint(0, 1) == 1:
        service_item["how_many"] = random.randint(1, 100)

    model = bc.database.create(
        service_stock_scheduler=1,
        plan=plan,
        service_item=service_item,
        mentorship_service=2,
        mentorship_service_set=1,
        service=service,
        **extra,
    )

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
        call("The consumable 1 for mentorship service set 1 was built"),
        call("The scheduler 1 was renewed"),
    ]
    assert logging.Logger.error.call_args_list == []

    assert bc.database.list_of("payments.Consumable") == [
        consumable_item(
            {
                "mentorship_service_set_id": 1,
                "id": 1,
                "service_item_id": 1,
                "user_id": 1,
                "how_many": model.service_item.how_many,
                "valid_until": UTC_NOW + relativedelta(minutes=5),
            }
        ),
    ]


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item",
    [
        ("plan_financing", True, False),
        ("subscription", False, True),
        ("subscription", True, False),
    ],
)
def test_two_event_types_linked(
    bc: Breathecode, type: str, plan_service_item_handler: bool, subscription_service_item: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if type == "subscription":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=4),
            "valid_until": UTC_NOW + relativedelta(minutes=5),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if plan_service_item_handler:
        extra["plan_service_item_handler"] = 1

    if subscription_service_item:
        extra["subscription_service_item"] = 1

    service = {"type": "EVENT_TYPE_SET"}
    plan = {"is_renewable": False}
    service_item = {"how_many": -1}
    if random.randint(0, 1) == 1:
        service_item["how_many"] = random.randint(1, 100)

    model = bc.database.create(
        service_stock_scheduler=1,
        plan=plan,
        service_item=service_item,
        event_type=2,
        event_type_set=1,
        service=service,
        **extra,
    )

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
        call("The consumable 1 for event type set 1 was built"),
        call("The scheduler 1 was renewed"),
    ]
    assert logging.Logger.error.call_args_list == []

    assert bc.database.list_of("payments.Consumable") == [
        consumable_item(
            {
                "event_type_set_id": 1,
                "id": 1,
                "service_item_id": 1,
                "user_id": 1,
                "how_many": model.service_item.how_many,
                "valid_until": UTC_NOW + relativedelta(minutes=5),
            }
        ),
    ]


#


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item",
    [
        ("plan_financing", True, False),
        ("subscription", False, True),
        ("subscription", True, False),
    ],
)
def test_without_a_resource_linked__type_void(
    bc: Breathecode, type: str, plan_service_item_handler: bool, subscription_service_item: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if type == "subscription":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=4),
            "valid_until": UTC_NOW + relativedelta(minutes=5),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if plan_service_item_handler:
        extra["plan_service_item_handler"] = 1

    if subscription_service_item:
        extra["subscription_service_item"] = 1

    service = {"type": "VOID"}
    plan = {"is_renewable": False}
    service_item = {"how_many": -1}
    if random.randint(0, 1) == 1:
        service_item["how_many"] = random.randint(1, 100)

    model = bc.database.create(
        service_stock_scheduler=1,
        plan=plan,
        service_item=service_item,
        service=service,
        **extra,
    )

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    print(bc.database.list_of("payments.Consumable"))
    print(logging.Logger.info.call_args_list)
    print(logging.Logger.error.call_args_list)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
        call("The consumable 1 was built"),
        call("The scheduler 1 was renewed"),
    ]
    assert logging.Logger.error.call_args_list == []

    assert bc.database.list_of("payments.Consumable") == [
        consumable_item(
            {
                "id": 1,
                "service_item_id": 1,
                "user_id": 1,
                "how_many": model.service_item.how_many,
                "valid_until": UTC_NOW + relativedelta(minutes=5),
            }
        ),
    ]


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item",
    [
        ("plan_financing", True, False),
        ("subscription", False, True),
        ("subscription", True, False),
    ],
)
def test_do_not_needs_renew(
    bc: Breathecode, type: str, plan_service_item_handler: bool, subscription_service_item: bool
):

    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if type == "subscription":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=4),
            "valid_until": UTC_NOW + relativedelta(minutes=5),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
        }

    if plan_service_item_handler:
        extra["plan_service_item_handler"] = 1

    if subscription_service_item:
        extra["subscription_service_item"] = 1

    service_stock_scheduler = {
        "valid_until": UTC_NOW - relativedelta(seconds=1),
    }
    plan = {"is_renewable": False}

    model = bc.database.create(
        service_stock_scheduler=service_stock_scheduler,
        plan=plan,
        mentorship_service=2,
        mentorship_service_set=1,
        **extra,
    )

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
        call("The scheduler 1 don't needs to be renewed"),
    ]
    assert logging.Logger.error.call_args_list == []

    assert bc.database.list_of("payments.Consumable") == []

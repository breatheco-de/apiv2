"""
Test /answer
"""

import logging
import random
from unittest.mock import MagicMock, call

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.contrib.auth.models import User

from breathecode.payments.models import SubscriptionBillingTeam, SubscriptionSeat
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
        "plan_financing_id": None,
        "subscription_id": None,
        "subscription_seat_id": None,
        "subscription_billing_team_id": None,
        **data,
    }


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    yield


def test_scheduler_not_found(database):
    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
        # retrying
        call("Starting renew_consumables for service stock scheduler 1"),
    ]
    assert logging.Logger.error.call_args_list == [
        call("ServiceStockScheduler with id 1 not found", exc_info=True),
    ]

    assert database.list_of("payments.Consumable") == []


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item",
    [
        ("plan_financing", True, False),
        ("subscription", False, True),
        ("subscription", True, False),
    ],
)
def test_is_over(database, type: str, plan_service_item_handler: bool, subscription_service_item: bool):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW - relativedelta(seconds=1),
            "valid_until": UTC_NOW - relativedelta(seconds=1),
            "seat_service_item_id": None,
        }

    if type == "subscription":
        extra[type] = {
            "valid_until": UTC_NOW - relativedelta(seconds=1),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "seat_service_item_id": None,
        }

    if plan_service_item_handler:
        extra["plan_service_item_handler"] = 1

    if subscription_service_item:
        extra["subscription_service_item"] = 1

    plan = {"is_renewable": False}
    academy = {"available_as_saas": True}
    service_item = {"how_many": -1}
    service = {"type": "SEAT"}  # SEAT services require how_many > 0

    model = database.create(
        service_stock_scheduler=1,
        plan=plan,
        academy=academy,
        country=1,
        city=1,
        service_item=service_item,
        service=service,
        **extra,
    )

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
    ]
    assert logging.Logger.error.call_args_list == [
        call(f"The {type.replace('_', ' ')} 1 is over", exc_info=True),
    ]

    assert database.list_of("payments.Consumable") == []


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item",
    [
        ("plan_financing", True, False),
        ("subscription", False, True),
        ("subscription", True, False),
    ],
)
def test_plan_financing_without_be_paid(
    database, type: str, plan_service_item_handler: bool, subscription_service_item: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=3),
            "valid_until": UTC_NOW + relativedelta(minutes=10),
            "next_payment_at": UTC_NOW - relativedelta(seconds=1),
            "seat_service_item_id": None,
        }

    if type == "subscription":
        extra[type] = {
            "valid_until": UTC_NOW + relativedelta(minutes=5),
            "next_payment_at": UTC_NOW - relativedelta(seconds=1),
            "seat_service_item_id": None,
        }

    if plan_service_item_handler:
        extra["plan_service_item_handler"] = 1

    if subscription_service_item:
        extra["subscription_service_item"] = 1

    plan = {"is_renewable": False}
    academy = {"available_as_saas": True}
    service_item = {"how_many": -1}
    service = {"type": "SEAT"}

    model = database.create(
        service_stock_scheduler=1,
        plan=plan,
        academy=academy,
        country=1,
        city=1,
        service_item=service_item,
        service=service,
        **extra,
    )

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
    ]
    assert logging.Logger.error.call_args_list == [
        call(f"The {type.replace('_', ' ')} 1 needs to be paid to renew the consumables", exc_info=True),
    ]

    assert database.list_of("payments.Consumable") == []


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item",
    [
        ("plan_financing", True, False),
        ("subscription", False, True),
        ("subscription", True, False),
    ],
)
def test_without_a_resource_linked(
    database, type: str, plan_service_item_handler: bool, subscription_service_item: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=3),
            "valid_until": UTC_NOW - relativedelta(seconds=1),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "seat_service_item_id": None,
        }

    if type == "subscription":
        extra[type] = {
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "seat_service_item_id": None,
        }

    if plan_service_item_handler:
        extra["plan_service_item_handler"] = 1

    if subscription_service_item:
        extra["subscription_service_item"] = 1

    plan = {"is_renewable": False}
    academy = {"available_as_saas": True}
    service_item = {"how_many": -1}
    service = {"type": "SEAT"}

    model = database.create(
        service_stock_scheduler=1,
        plan=plan,
        academy=academy,
        country=1,
        city=1,
        service_item=service_item,
        service=service,
        **extra,
    )

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
    ]
    assert logging.Logger.error.call_args_list == [
        call("The Plan not have a resource linked to it for the ServiceStockScheduler 1"),
    ]

    assert database.list_of("payments.Consumable") == []


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item, with_seat",
    [
        ("plan_financing", True, False, False),
        ("subscription", False, True, False),
        ("subscription", True, False, False),
        ("subscription", False, True, True),
        ("subscription", True, False, True),
    ],
)
def test_with_two_cohorts_linked(
    database, type: str, plan_service_item_handler: bool, subscription_service_item: bool, with_seat: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "seat_service_item_id": None,
        }

    if type == "subscription":
        extra[type] = {
            "valid_until": UTC_NOW + relativedelta(minutes=3),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "seat_service_item_id": None,
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

    # Always create the scheduler; if with_seat, also create a subscription to attach the seat

    base_kwargs = {
        "service_stock_scheduler": 1,
        "plan": plan,
        "service_item": service_item,
        "cohort": 2,
        "cohort_set": 2,
        "academy": academy,
        "country": 1,
        "city": 1,
        "service": {"type": "COHORT_SET"},
        **extra,
    }

    # Create a separate SEAT service and service_item for any seat validation needs
    seat_model = database.create(service={"type": "SEAT"}, service_item={"how_many": 1})

    # Ensure any subscription model explicitly sets seat_service_item appropriately
    if "subscription" in base_kwargs:
        if isinstance(base_kwargs["subscription"], dict):
            # Only set seat_service_item if with_seat is True, otherwise explicitly set to None
            if with_seat:
                base_kwargs["subscription"]["seat_service_item"] = seat_model.service_item
            else:
                base_kwargs["subscription"]["seat_service_item"] = None
        else:
            # If it's just a number (creating default), create dict with explicit seat_service_item
            if with_seat:
                base_kwargs["subscription"] = {"seat_service_item": seat_model.service_item}
            else:
                base_kwargs["subscription"] = {"seat_service_item": None}
    # Enforce: plan_financing never carries seat_service_item regardless of with_seat
    if "plan_financing" in base_kwargs:
        if isinstance(base_kwargs["plan_financing"], dict):
            # Only set seat_service_item if with_seat is True, otherwise explicitly set to None
            if with_seat:
                base_kwargs["plan_financing"]["seat_service_item"] = seat_model.service_item
            else:
                base_kwargs["plan_financing"]["seat_service_item"] = None
        else:
            # If it's just a number (creating default), create dict with explicit seat_service_item
            if with_seat:
                base_kwargs["plan_financing"] = {
                    **base_kwargs["plan_financing"],
                    "seat_service_item": seat_model.service_item,
                }
            else:
                base_kwargs["plan_financing"] = {**base_kwargs["plan_financing"], "seat_service_item": None}

    model = database.create(**base_kwargs)

    # When requested, create a team + seat and assign to the scheduler
    if with_seat:
        team = SubscriptionBillingTeam.objects.create(
            subscription=model.subscription, name=f"Team {model.subscription.id}", seats_limit=5
        )
        # Create a distinct user for the seat to verify consumable ownership is the seat user
        member_user = User.objects.create(
            username=f"member{model.subscription.id}", email=f"member{model.subscription.id}@example.com"
        )
        seat = SubscriptionSeat.objects.create(
            billing_team=team, user=member_user, email=member_user.email, is_active=True, seat_multiplier=1
        )
        scheduler = model.service_stock_scheduler
        scheduler.subscription_seat = seat
        scheduler.save()

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
        call("The consumable 1 for cohort set 1 was built"),
        call("The scheduler 1 was renewed"),
    ]
    assert logging.Logger.error.call_args_list == []

    expected_user_id = seat.user.id if (with_seat and type == "subscription") else 1

    assert database.list_of("payments.Consumable") == [
        consumable_item(
            {
                "cohort_set_id": 1,
                "id": 1,
                "service_item_id": 2,
                "user_id": expected_user_id,
                "how_many": model.service_item.how_many,
                "valid_until": UTC_NOW
                + (relativedelta(minutes=5) if type == "plan_financing" else relativedelta(minutes=3)),
                "plan_financing_id": 1 if type == "plan_financing" else None,
                "subscription_id": 1 if type == "subscription" else None,
                "subscription_seat_id": 1 if with_seat else None,
            }
        ),
    ]


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item, with_seat",
    [
        ("plan_financing", True, False, False),
        ("subscription", False, True, False),
        ("subscription", True, False, False),
        ("subscription", False, True, True),
        ("subscription", True, False, True),
    ],
)
def test_two_mentorship_services_linked(
    database, type: str, plan_service_item_handler: bool, subscription_service_item: bool, with_seat: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "seat_service_item_id": None,
        }

    if type == "subscription":
        extra[type] = {
            "valid_until": UTC_NOW + relativedelta(minutes=5),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "seat_service_item_id": None,
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
    academy = {"available_as_saas": True}

    # Build base kwargs and optionally include a subscription
    base_kwargs = {
        "service_stock_scheduler": 1,
        "plan": plan,
        "service_item": service_item,
        "mentorship_service": 2,
        "mentorship_service_set": 1,
        "service": {"type": "MENTORSHIP_SERVICE_SET"},
        "academy": academy,
        "country": 1,
        "city": 1,
        **extra,
    }
    if with_seat:
        base_kwargs["subscription"]["seat_service_item_id"] = 2
        base_kwargs["service"] = [base_kwargs["service"], {"type": "SEAT"}]
        base_kwargs["service_item"] = [service_item, {"how_many": 3, "service_id": 2}]
    model = database.create(**base_kwargs)

    if with_seat:
        team = SubscriptionBillingTeam.objects.create(
            subscription=model.subscription, name=f"Team {model.subscription.id}", seats_limit=5
        )
        member_user = User.objects.create(
            username=f"member{model.subscription.id}", email=f"member{model.subscription.id}@example.com"
        )
        seat = SubscriptionSeat.objects.create(
            billing_team=team, user=member_user, email=member_user.email, is_active=True, seat_multiplier=1
        )
        scheduler = model.service_stock_scheduler
        scheduler.subscription_seat = seat
        scheduler.save()

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
        call("The consumable 1 for mentorship service set 1 was built"),
        call("The scheduler 1 was renewed"),
    ]
    assert logging.Logger.error.call_args_list == []

    expected_user_id = seat.user.id if (with_seat and type == "subscription") else 1

    assert database.list_of("payments.Consumable") == [
        consumable_item(
            {
                "mentorship_service_set_id": 1,
                "id": 1,
                "service_item_id": 1,
                "user_id": expected_user_id,
                "how_many": (
                    model.service_item[0].how_many
                    if isinstance(model.service_item, list)
                    else model.service_item.how_many
                ),
                "valid_until": UTC_NOW + relativedelta(minutes=5),
                "plan_financing_id": 1 if type == "plan_financing" else None,
                "subscription_id": 1 if type == "subscription" else None,
                "subscription_seat_id": 1 if with_seat else None,
            }
        ),
    ]


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item, with_seat",
    [
        ("plan_financing", True, False, False),
        ("subscription", False, True, False),
        ("subscription", True, False, False),
        ("subscription", False, True, True),
        ("subscription", True, False, True),
    ],
)
def test_two_event_types_linked(
    database, type: str, plan_service_item_handler: bool, subscription_service_item: bool, with_seat: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "seat_service_item_id": None,
        }

    if type == "subscription":
        extra[type] = {
            "valid_until": UTC_NOW + relativedelta(minutes=5),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "seat_service_item_id": None,
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
    academy = {"available_as_saas": True}

    base_kwargs = {
        "service_stock_scheduler": 1,
        "plan": plan,
        "service_item": service_item,
        "event_type": [{"description": "e1"}, {"description": "e2"}],
        "event_type_set": 1,
        "service": {"type": "EVENT_TYPE_SET"},
        "academy": academy,
        "country": 1,
        "city": 1,
        **extra,
    }
    if with_seat:
        base_kwargs["subscription"]["seat_service_item_id"] = 2
        base_kwargs["service"] = [base_kwargs["service"], {"type": "SEAT"}]
        base_kwargs["service_item"] = [service_item, {"how_many": 3, "service_id": 2}]
    model = database.create(**base_kwargs)

    if with_seat:
        team = SubscriptionBillingTeam.objects.create(
            subscription=model.subscription, name=f"Team {model.subscription.id}", seats_limit=5
        )
        member_user = User.objects.create(
            username=f"member{model.subscription.id}", email=f"member{model.subscription.id}@example.com"
        )
        seat = SubscriptionSeat.objects.create(
            billing_team=team, user=member_user, email=member_user.email, is_active=True, seat_multiplier=1
        )
        scheduler = model.service_stock_scheduler
        scheduler.subscription_seat = seat
        scheduler.save()

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
        call("The consumable 1 for event type set 1 was built"),
        call("The scheduler 1 was renewed"),
    ]
    assert logging.Logger.error.call_args_list == []

    expected_user_id = seat.user.id if (with_seat and type == "subscription") else 1

    assert database.list_of("payments.Consumable") == [
        consumable_item(
            {
                "event_type_set_id": 1,
                "id": 1,
                "service_item_id": 1,
                "user_id": expected_user_id,
                "how_many": (
                    model.service_item[0].how_many
                    if isinstance(model.service_item, list)
                    else model.service_item.how_many
                ),
                "valid_until": UTC_NOW + relativedelta(minutes=5),
                "plan_financing_id": 1 if type == "plan_financing" else None,
                "subscription_id": 1 if type == "subscription" else None,
                "subscription_seat_id": 1 if with_seat else None,
            }
        ),
    ]


#


@pytest.mark.parametrize(
    "type, plan_service_item_handler, subscription_service_item, with_seat",
    [
        ("plan_financing", True, False, False),
        ("subscription", False, True, False),
        ("subscription", True, False, False),
        ("subscription", False, True, True),
        ("subscription", True, False, True),
    ],
)
def test_without_a_resource_linked__type_void(
    database, type: str, plan_service_item_handler: bool, subscription_service_item: bool, with_seat: bool
):
    extra = {}

    if type == "plan_financing":
        extra[type] = {
            "monthly_price": random.random() * 99.99 + 0.01,
            "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
            "valid_until": UTC_NOW - relativedelta(seconds=4),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "seat_service_item_id": None,
        }

    if type == "subscription":
        extra[type] = {
            "valid_until": UTC_NOW + relativedelta(minutes=5),
            "next_payment_at": UTC_NOW + relativedelta(minutes=3),
            "seat_service_item_id": None,
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

    base_kwargs = {
        "service_stock_scheduler": 1,
        "plan": plan,
        "service_item": service_item,
        "service": {"type": "VOID"},
        "academy": academy,
        "country": 1,
        "city": 1,
        **extra,
    }
    if with_seat:
        base_kwargs["subscription"]["seat_service_item_id"] = 2
        base_kwargs["service"] = [base_kwargs["service"], {"type": "SEAT"}]
        base_kwargs["service_item"] = [service_item, {"how_many": 3, "service_id": 2}]

    model = database.create(**base_kwargs)

    if with_seat:
        team = SubscriptionBillingTeam.objects.create(
            subscription=model.subscription, name=f"Team {model.subscription.id}", seats_limit=5
        )
        member_user = User.objects.create(
            username=f"member{model.subscription.id}", email=f"member{model.subscription.id}@example.com"
        )
        seat = SubscriptionSeat.objects.create(
            billing_team=team, user=member_user, email=member_user.email, is_active=True, seat_multiplier=1
        )
        scheduler = model.service_stock_scheduler
        scheduler.subscription_seat = seat
        scheduler.save()

    logging.Logger.info.call_args_list = []
    logging.Logger.error.call_args_list = []

    renew_consumables.delay(1)

    assert logging.Logger.info.call_args_list == [
        call("Starting renew_consumables for service stock scheduler 1"),
        call("The consumable 1 was built"),
        call("The scheduler 1 was renewed"),
    ]
    assert logging.Logger.error.call_args_list == []

    expected_user_id = seat.user.id if (with_seat and type == "subscription") else 1

    assert database.list_of("payments.Consumable") == [
        consumable_item(
            {
                "id": 1,
                "service_item_id": 1,
                "user_id": expected_user_id,
                "how_many": (
                    model.service_item[0].how_many
                    if isinstance(model.service_item, list)
                    else model.service_item.how_many
                ),
                "valid_until": UTC_NOW + relativedelta(minutes=5),
                "plan_financing_id": 1 if type == "plan_financing" else None,
                "subscription_id": 1 if type == "subscription" else None,
                "subscription_seat_id": 1 if with_seat else None,
            }
        ),
    ]


# this case seems like it was deleted, it means the task is not checking if the consumables were renewed
# @pytest.mark.parametrize(
#     "type, plan_service_item_handler, subscription_service_item",
#     [
#         ("plan_financing", True, False),
#         ("subscription", False, True),
#         ("subscription", True, False),
#     ],
# )
# def test_do_not_needs_renew(
#     bc: Breathecode, type: str, plan_service_item_handler: bool, subscription_service_item: bool
# ):

#     extra = {}

#     if type == "plan_financing":
#         extra[type] = {
#             "monthly_price": random.random() * 99.99 + 0.01,
#             "plan_expires_at": UTC_NOW + relativedelta(minutes=5),
#             "valid_until": UTC_NOW - relativedelta(seconds=4),
#             "next_payment_at": UTC_NOW + relativedelta(minutes=3),
#         }

#     if type == "subscription":
#         extra[type] = {
#             "monthly_price": random.random() * 99.99 + 0.01,
#             "plan_expires_at": UTC_NOW - relativedelta(seconds=4),
#             "valid_until": UTC_NOW + relativedelta(minutes=5),
#             "next_payment_at": UTC_NOW + relativedelta(minutes=3),
#         }

#     if plan_service_item_handler:
#         extra["plan_service_item_handler"] = 1

#     if subscription_service_item:
#         extra["subscription_service_item"] = 1

#     service_stock_scheduler = {
#         "valid_until": UTC_NOW - relativedelta(seconds=1),
#     }
#     plan = {"is_renewable": False}

#     model = bc.database.create(
#         service_stock_scheduler=service_stock_scheduler,
#         plan=plan,
#         mentorship_service=2,
#         mentorship_service_set=1,
#         **extra,
#     )

#     logging.Logger.info.call_args_list = []
#     logging.Logger.error.call_args_list = []

#     renew_consumables.delay(1)

#     assert logging.Logger.info.call_args_list == [
#         call("Starting renew_consumables for service stock scheduler 1"),
#         call("The scheduler 1 don't needs to be renewed"),
#     ]
#     assert logging.Logger.error.call_args_list == []

#     assert bc.database.list_of("payments.Consumable") == []

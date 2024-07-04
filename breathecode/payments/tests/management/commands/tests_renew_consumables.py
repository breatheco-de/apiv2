import random
from unittest.mock import patch, MagicMock, call

import pytest
from breathecode.payments import tasks
from breathecode.payments.management.commands.renew_consumables import Command
from breathecode.payments.tests.mixins import PaymentsTestCase
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def apply_patch(db, monkeypatch):
    m1 = MagicMock()
    m2 = MagicMock()
    monkeypatch.setattr(tasks.renew_subscription_consumables, "delay", m1)
    monkeypatch.setattr(tasks.renew_plan_financing_consumables, "delay", m2)
    yield m1, m2


def test_no_related_entities(bc: Breathecode):
    command = Command()
    result = command.handle()

    assert result == None

    assert bc.database.list_of("payments.Subscription") == []
    assert bc.database.list_of("payments.PlanFinancing") == []

    assert tasks.renew_subscription_consumables.delay.call_args_list == []
    assert tasks.renew_plan_financing_consumables.delay.call_args_list == []


def invalid_statuses_params():
    for entity in ["subscription", "plan_financing"]:
        for status in ["CANCELLED", "DEPRECATED"]:
            entity_attrs = {
                "status": status,
            }

            yield entity, entity_attrs


@pytest.mark.parametrize("entity,entity_attrs", invalid_statuses_params())
def test_no_schedulers__invalid_statuses(bc: Breathecode, entity, entity_attrs):
    if entity == "plan_financing":
        entity_attrs["monthly_price"] = 10
        entity_attrs["plan_expires_at"] = bc.datetime.now()

    extra = {entity: (2, entity_attrs)}

    model = bc.database.create(**extra)

    command = Command()
    result = command.handle()

    assert result == None

    if entity == "subscription":
        assert bc.database.list_of("payments.Subscription") == bc.format.to_dict(model.subscription)
        assert bc.database.list_of("payments.PlanFinancing") == []

    elif entity == "plan_financing":
        assert bc.database.list_of("payments.Subscription") == []
        assert bc.database.list_of("payments.PlanFinancing") == bc.format.to_dict(model.plan_financing)

    assert tasks.renew_subscription_consumables.delay.call_args_list == []
    assert tasks.renew_plan_financing_consumables.delay.call_args_list == []


def valid_statuses_params():
    for entity in ["subscription", "plan_financing"]:
        statuses = ["FREE_TRIAL", "ACTIVE", "ERROR", "EXPIRED"]
        if entity != "subscription":
            statuses.append("FULLY_PAID")

        for status in statuses:
            entity_attrs = {
                "status": status,
            }

            yield entity, entity_attrs


@pytest.mark.parametrize("entity,entity_attrs", valid_statuses_params())
def test_no_schedulers__valid_statuses(bc: Breathecode, entity, entity_attrs):
    if entity == "plan_financing":
        entity_attrs["monthly_price"] = 10
        entity_attrs["plan_expires_at"] = bc.datetime.now()

    extra = {entity: (2, entity_attrs)}

    model = bc.database.create(**extra)

    command = Command()
    result = command.handle()

    assert result == None

    if entity == "subscription":
        assert bc.database.list_of("payments.Subscription") == bc.format.to_dict(model.subscription)
        assert bc.database.list_of("payments.PlanFinancing") == []

        assert tasks.renew_subscription_consumables.delay.call_args_list == [call(1), call(2)]
        assert tasks.renew_plan_financing_consumables.delay.call_args_list == []

    elif entity == "plan_financing":
        assert bc.database.list_of("payments.Subscription") == []
        assert bc.database.list_of("payments.PlanFinancing") == bc.format.to_dict(model.plan_financing)

        assert tasks.renew_subscription_consumables.delay.call_args_list == []
        assert tasks.renew_plan_financing_consumables.delay.call_args_list == [call(1), call(2)]


def valid_statuses_params():
    for entity in ["subscription", "plan_financing"]:
        statuses = ["FREE_TRIAL", "ACTIVE", "ERROR", "EXPIRED"]
        if entity != "subscription":
            statuses.append("FULLY_PAID")

        for status in statuses:
            entity_attrs = {
                "status": status,
            }

            yield entity, entity_attrs


@pytest.mark.parametrize("entity,entity_attrs", valid_statuses_params())
def test_this_resource_does_not_requires_a_renovation(bc: Breathecode, entity, entity_attrs):
    if entity == "plan_financing":
        entity_attrs["monthly_price"] = 10
        entity_attrs["plan_expires_at"] = bc.datetime.now()

    extra = {entity: (2, entity_attrs)}

    consumable = {
        "valid_until": bc.datetime.now() + relativedelta(hours=2, days=random.randint(1, 31)),
    }

    plan = {
        "is_renewable": False,
        "time_of_life": random.randint(1, 31),
        "time_of_life_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
        "price_per_month": random.randint(1, 31),
        "price_per_year": random.randint(1, 31),
        "price_per_quarter": random.randint(1, 31),
        "price_per_half": random.randint(1, 31),
    }

    service_stock_schedulers = [{"consumables": [n]} for n in range(1, 3)]
    plan_service_item_handlers = [{entity + "_id": n} for n in range(1, 3)]

    model = bc.database.create(
        **extra,
        consumable=(2, consumable),
        service_stock_scheduler=service_stock_schedulers,
        plan_service_item_handler=plan_service_item_handlers,
        plan=plan
    )

    command = Command()
    result = command.handle()

    assert result == None

    if entity == "subscription":
        assert bc.database.list_of("payments.Subscription") == bc.format.to_dict(model.subscription)
        assert bc.database.list_of("payments.PlanFinancing") == []

    else:
        assert bc.database.list_of("payments.Subscription") == []
        assert bc.database.list_of("payments.PlanFinancing") == bc.format.to_dict(model.plan_financing)

    assert tasks.renew_subscription_consumables.delay.call_args_list == []
    assert tasks.renew_plan_financing_consumables.delay.call_args_list == []


@pytest.mark.parametrize("entity,entity_attrs", valid_statuses_params())
def test_this_resource_requires_a_renovation(bc: Breathecode, entity, entity_attrs):
    if entity == "plan_financing":
        entity_attrs["monthly_price"] = 10
        entity_attrs["plan_expires_at"] = bc.datetime.now()

    extra = {entity: (2, entity_attrs)}

    consumable = {
        "valid_until": bc.datetime.now() - relativedelta(hours=2, days=random.randint(1, 31)),
    }

    plan = {
        "is_renewable": False,
        "time_of_life": random.randint(1, 31),
        "time_of_life_unit": random.choice(["DAY", "WEEK", "MONTH", "YEAR"]),
        "price_per_month": random.randint(1, 31),
        "price_per_year": random.randint(1, 31),
        "price_per_quarter": random.randint(1, 31),
        "price_per_half": random.randint(1, 31),
    }

    service_stock_schedulers = [{"consumables": [n]} for n in range(1, 3)]
    plan_service_item_handlers = [{entity + "_id": n} for n in range(1, 3)]

    model = bc.database.create(
        **extra,
        consumable=(2, consumable),
        service_stock_scheduler=service_stock_schedulers,
        plan_service_item_handler=plan_service_item_handlers,
        plan=plan
    )

    command = Command()
    result = command.handle()

    assert result == None

    if entity == "subscription":
        assert bc.database.list_of("payments.Subscription") == bc.format.to_dict(model.subscription)
        assert bc.database.list_of("payments.PlanFinancing") == []

        assert tasks.renew_subscription_consumables.delay.call_args_list == [call(1), call(2)]
        assert tasks.renew_plan_financing_consumables.delay.call_args_list == []

    elif entity == "plan_financing":
        assert bc.database.list_of("payments.Subscription") == []
        assert bc.database.list_of("payments.PlanFinancing") == bc.format.to_dict(model.plan_financing)

        assert tasks.renew_subscription_consumables.delay.call_args_list == []
        assert tasks.renew_plan_financing_consumables.delay.call_args_list == [call(1), call(2)]

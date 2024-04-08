import sys
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from bc.django.pytest import fixtures as fx
from breathecode.payments import tasks
from breathecode.payments.management.commands.reschedule_bags import Command
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def apply_patch(db, monkeypatch: pytest.MonkeyPatch):
    m1 = MagicMock()
    m2 = MagicMock()
    m3 = MagicMock()
    monkeypatch.setattr(tasks.build_plan_financing, 'delay', m1)
    monkeypatch.setattr(tasks.build_subscription, 'delay', m2)
    monkeypatch.setattr(tasks.build_free_subscription, 'delay', m3)

    yield m1, m2, m3


@pytest.mark.parametrize('bags, in_the_past', [
    (0, False),
    ((2, {
        'was_delivered': True,
        'status': 'RENEWAL',
    }), False),
    ((2, {
        'was_delivered': True,
        'status': 'CHECKING',
    }), False),
    ((2, {
        'was_delivered': True,
        'status': 'PAID',
    }), False),
    ((2, {
        'was_delivered': False,
        'status': 'RENEWAL',
    }), True),
    ((2, {
        'was_delivered': False,
        'status': 'CHECKING',
    }), True),
])
def test_nothing_to_process(bc: Breathecode, bags, in_the_past):
    model = bc.database.create(bag=bags)

    command = Command()
    # command.stdout.write = out_mock
    result = command.handle()

    assert result == None

    db = []
    if bags:
        db = bc.format.to_dict(model.bag)
    assert bc.database.list_of('payments.Bag') == db

    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []


@pytest.mark.parametrize('bags, invoices, type', [
    ((2, {
        'was_delivered': False,
        'status': 'PAID',
        'how_many_installments': 0,
    }), {
        'amount': 0,
    }, 'free'),
    ((2, {
        'was_delivered': False,
        'status': 'PAID',
        'how_many_installments': 2,
    }), {
        'amount': 0,
    }, 'financing'),
    ((2, {
        'was_delivered': False,
        'status': 'PAID',
        'how_many_installments': 0,
    }), {
        'amount': 2,
    }, 'subscription'),
])
def test_rescheduling_bags(bc: Breathecode, bags, invoices, type, utc_now, set_datetime):
    model = bc.database.create(bag=bags, invoice=invoices)
    set_datetime(utc_now + timedelta(minutes=11))

    command = Command()
    result = command.handle()

    assert result == None

    db = bc.format.to_dict(model.bag)
    assert bc.database.list_of('payments.Bag') == db

    if type == 'free':
        assert tasks.build_plan_financing.delay.call_args_list == []
        assert tasks.build_subscription.delay.call_args_list == []
        assert tasks.build_free_subscription.delay.call_args_list == [call(1, 1)]

    elif type == 'financing':
        assert tasks.build_plan_financing.delay.call_args_list == [call(1, 1)]
        assert tasks.build_subscription.delay.call_args_list == []
        assert tasks.build_free_subscription.delay.call_args_list == []

    elif type == 'subscription':
        assert tasks.build_plan_financing.delay.call_args_list == []
        assert tasks.build_subscription.delay.call_args_list == [call(1, 1)]
        assert tasks.build_free_subscription.delay.call_args_list == []

    else:
        assert 0, 'type value is mandatory'


# def invalid_statuses_params():
#     for entity in ['subscription', 'plan_financing']:
#         for status in ['CANCELLED', 'DEPRECATED']:
#             entity_attrs = {
#                 'status': status,
#             }

#             yield entity, entity_attrs

# @pytest.mark.parametrize('entity,entity_attrs', invalid_statuses_params())
# def test_no_schedulers__invalid_statuses(bc: Breathecode, entity, entity_attrs):
#     if entity == 'plan_financing':
#         entity_attrs['monthly_price'] = 10
#         entity_attrs['plan_expires_at'] = bc.datetime.now()

#     extra = {entity: (2, entity_attrs)}

#     model = bc.database.create(**extra)

#     command = Command()
#     result = command.handle()

#     assert result == None

#     if entity == 'subscription':
#         assert bc.database.list_of('payments.Subscription') == bc.format.to_dict(model.subscription)
#         assert bc.database.list_of('payments.PlanFinancing') == []

#     elif entity == 'plan_financing':
#         assert bc.database.list_of('payments.Subscription') == []
#         assert bc.database.list_of('payments.PlanFinancing') == bc.format.to_dict(model.plan_financing)

#     assert tasks.renew_subscription_consumables.delay.call_args_list == []
#     assert tasks.renew_plan_financing_consumables.delay.call_args_list == []

# def valid_statuses_params():
#     for entity in ['subscription', 'plan_financing']:
#         statuses = ['FREE_TRIAL', 'ACTIVE', 'ERROR', 'EXPIRED']
#         if entity != 'subscription':
#             statuses.append('FULLY_PAID')

#         for status in statuses:
#             entity_attrs = {
#                 'status': status,
#             }

#             yield entity, entity_attrs

# @pytest.mark.parametrize('entity,entity_attrs', valid_statuses_params())
# def test_no_schedulers__valid_statuses(bc: Breathecode, entity, entity_attrs):
#     if entity == 'plan_financing':
#         entity_attrs['monthly_price'] = 10
#         entity_attrs['plan_expires_at'] = bc.datetime.now()

#     extra = {entity: (2, entity_attrs)}

#     model = bc.database.create(**extra)

#     command = Command()
#     result = command.handle()

#     assert result == None

#     if entity == 'subscription':
#         assert bc.database.list_of('payments.Subscription') == bc.format.to_dict(model.subscription)
#         assert bc.database.list_of('payments.PlanFinancing') == []

#         assert tasks.renew_subscription_consumables.delay.call_args_list == [call(1), call(2)]
#         assert tasks.renew_plan_financing_consumables.delay.call_args_list == []

#     elif entity == 'plan_financing':
#         assert bc.database.list_of('payments.Subscription') == []
#         assert bc.database.list_of('payments.PlanFinancing') == bc.format.to_dict(model.plan_financing)

#         assert tasks.renew_subscription_consumables.delay.call_args_list == []
#         assert tasks.renew_plan_financing_consumables.delay.call_args_list == [call(1), call(2)]

# def valid_statuses_params():
#     for entity in ['subscription', 'plan_financing']:
#         statuses = ['FREE_TRIAL', 'ACTIVE', 'ERROR', 'EXPIRED']
#         if entity != 'subscription':
#             statuses.append('FULLY_PAID')

#         for status in statuses:
#             entity_attrs = {
#                 'status': status,
#             }

#             yield entity, entity_attrs

# @pytest.mark.parametrize('entity,entity_attrs', valid_statuses_params())
# def test_this_resource_does_not_requires_a_renovation(bc: Breathecode, entity, entity_attrs):
#     if entity == 'plan_financing':
#         entity_attrs['monthly_price'] = 10
#         entity_attrs['plan_expires_at'] = bc.datetime.now()

#     extra = {entity: (2, entity_attrs)}

#     consumable = {
#         'valid_until': bc.datetime.now() + relativedelta(hours=2, days=random.randint(1, 31)),
#     }

#     plan = {
#         'is_renewable': False,
#         'time_of_life': random.randint(1, 31),
#         'time_of_life_unit': random.choice(['DAY', 'WEEK', 'MONTH', 'YEAR']),
#         'price_per_month': random.randint(1, 31),
#         'price_per_year': random.randint(1, 31),
#         'price_per_quarter': random.randint(1, 31),
#         'price_per_half': random.randint(1, 31),
#     }

#     service_stock_schedulers = [{'consumables': [n]} for n in range(1, 3)]
#     plan_service_item_handlers = [{entity + '_id': n} for n in range(1, 3)]

#     model = bc.database.create(**extra,
#                                consumable=(2, consumable),
#                                service_stock_scheduler=service_stock_schedulers,
#                                plan_service_item_handler=plan_service_item_handlers,
#                                plan=plan)

#     command = Command()
#     result = command.handle()

#     assert result == None

#     if entity == 'subscription':
#         assert bc.database.list_of('payments.Subscription') == bc.format.to_dict(model.subscription)
#         assert bc.database.list_of('payments.PlanFinancing') == []

#     else:
#         assert bc.database.list_of('payments.Subscription') == []
#         assert bc.database.list_of('payments.PlanFinancing') == bc.format.to_dict(model.plan_financing)

#     assert tasks.renew_subscription_consumables.delay.call_args_list == []
#     assert tasks.renew_plan_financing_consumables.delay.call_args_list == []

# @pytest.mark.parametrize('entity,entity_attrs', valid_statuses_params())
# def test_this_resource_requires_a_renovation(bc: Breathecode, entity, entity_attrs):
#     if entity == 'plan_financing':
#         entity_attrs['monthly_price'] = 10
#         entity_attrs['plan_expires_at'] = bc.datetime.now()

#     extra = {entity: (2, entity_attrs)}

#     consumable = {
#         'valid_until': bc.datetime.now() - relativedelta(hours=2, days=random.randint(1, 31)),
#     }

#     plan = {
#         'is_renewable': False,
#         'time_of_life': random.randint(1, 31),
#         'time_of_life_unit': random.choice(['DAY', 'WEEK', 'MONTH', 'YEAR']),
#         'price_per_month': random.randint(1, 31),
#         'price_per_year': random.randint(1, 31),
#         'price_per_quarter': random.randint(1, 31),
#         'price_per_half': random.randint(1, 31),
#     }

#     service_stock_schedulers = [{'consumables': [n]} for n in range(1, 3)]
#     plan_service_item_handlers = [{entity + '_id': n} for n in range(1, 3)]

#     model = bc.database.create(**extra,
#                                consumable=(2, consumable),
#                                service_stock_scheduler=service_stock_schedulers,
#                                plan_service_item_handler=plan_service_item_handlers,
#                                plan=plan)

#     command = Command()
#     result = command.handle()

#     assert result == None

#     if entity == 'subscription':
#         assert bc.database.list_of('payments.Subscription') == bc.format.to_dict(model.subscription)
#         assert bc.database.list_of('payments.PlanFinancing') == []

#         assert tasks.renew_subscription_consumables.delay.call_args_list == [call(1), call(2)]
#         assert tasks.renew_plan_financing_consumables.delay.call_args_list == []

#     elif entity == 'plan_financing':
#         assert bc.database.list_of('payments.Subscription') == []
#         assert bc.database.list_of('payments.PlanFinancing') == bc.format.to_dict(model.plan_financing)

#         assert tasks.renew_subscription_consumables.delay.call_args_list == []
#         assert tasks.renew_plan_financing_consumables.delay.call_args_list == [call(1), call(2)]

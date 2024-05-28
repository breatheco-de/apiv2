import random
from unittest.mock import MagicMock, call, patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.management.commands.make_charges import Command
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def setup(db: None, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(tasks.charge_subscription, 'delay', MagicMock())
    monkeypatch.setattr(tasks.charge_plan_financing, 'delay', MagicMock())


def test_with_zero_subscriptions(bc: Breathecode):
    command = Command()
    result = command.handle()

    assert result == None
    assert bc.database.list_of('payments.Subscription') == []
    assert tasks.charge_subscription.delay.call_args_list == []


@pytest.mark.parametrize('delta, status', [
    (relativedelta(days=1, minutes=1), 'ACTIVE'),
    (relativedelta(days=1, minutes=1), 'ERROR'),
    (relativedelta(days=1, minutes=1), 'PAYMENT_ISSUE'),
    (-relativedelta(days=1, seconds=1), 'CANCELLED'),
    (-relativedelta(days=1, seconds=1), 'FREE_TRIAL'),
    (-relativedelta(days=1, seconds=1), 'DEPRECATED'),
])
def test_with_two_subscriptions__wrong_cases(bc: Breathecode, delta, status, utc_now):
    valid_until = utc_now + delta
    subscription = {'valid_until': valid_until, 'next_payment_at': valid_until, 'status': status}

    model = bc.database.create(subscription=(2, subscription))

    command = Command()
    result = command.handle()

    assert result == None
    assert bc.database.list_of('payments.Subscription') == bc.format.to_dict(model.subscription)
    assert tasks.charge_subscription.delay.call_args_list == []


@pytest.mark.parametrize('delta, status, status_changed', [
    (-relativedelta(days=1, seconds=1), 'ACTIVE', True),
    (-relativedelta(days=1, seconds=1), 'ERROR', False),
    (-relativedelta(days=1, seconds=1), 'PAYMENT_ISSUE', False),
])
def test_with_two_subscriptions__expired(bc: Breathecode, delta, status, status_changed, utc_now):
    valid_until = utc_now + delta
    subscription = {'valid_until': valid_until, 'next_payment_at': valid_until, 'status': status}

    model = bc.database.create(subscription=(2, subscription))

    command = Command()
    result = command.handle()

    assert result == None
    db = bc.format.to_dict(model.subscription)
    for i in range(len(db)):
        if status_changed:
            db[i]['status'] = 'EXPIRED'

    assert bc.database.list_of('payments.Subscription') == db
    assert tasks.charge_subscription.delay.call_args_list == []


@pytest.mark.parametrize('delta, status', [
    (relativedelta(days=2, seconds=1), 'ACTIVE'),
    (relativedelta(days=2, seconds=1), 'ERROR'),
    (relativedelta(days=2, seconds=1), 'PAYMENT_ISSUE'),
])
def test_with_two_subscriptions__valid_cases(bc: Breathecode, delta, status, utc_now):
    valid_until = utc_now + delta
    next_payment_at = utc_now - delta
    subscription = {'valid_until': valid_until, 'next_payment_at': next_payment_at, 'status': status}

    model = bc.database.create(subscription=(2, subscription))

    command = Command()
    result = command.handle()

    assert result == None
    assert bc.database.list_of('payments.Subscription') == bc.format.to_dict(model.subscription)
    assert tasks.charge_subscription.delay.call_args_list == [
        call(model.subscription[0].id),
        call(model.subscription[1].id),
    ]


# 🔽🔽🔽 PlanFinancing cases


def test_with_zero_plan_financings(bc: Breathecode):
    command = Command()
    result = command.handle()

    assert result == None
    assert bc.database.list_of('payments.PlanFinancing') == []
    assert tasks.charge_plan_financing.delay.call_args_list == []


@pytest.mark.parametrize('delta, status', [
    (relativedelta(days=1, minutes=1), 'ACTIVE'),
    (relativedelta(days=1, minutes=1), 'ERROR'),
    (relativedelta(days=1, minutes=1), 'PAYMENT_ISSUE'),
    (-relativedelta(days=1, seconds=1), 'CANCELLED'),
    (-relativedelta(days=1, seconds=1), 'FREE_TRIAL'),
    (-relativedelta(days=1, seconds=1), 'DEPRECATED'),
])
def test_with_two_plan_financings__wrong_cases(bc: Breathecode, delta, status, utc_now):
    valid_until = utc_now + delta
    plan_financing = {
        'next_payment_at': valid_until,
        'valid_until': UTC_NOW + relativedelta(months=random.randint(12, 24)),
        'status': status,
        'monthly_price': (random.random() * 99) + 1,
        'plan_expires_at': UTC_NOW + relativedelta(months=random.randint(1, 12)),
    }

    model = bc.database.create(plan_financing=(2, plan_financing))

    command = Command()
    result = command.handle()

    assert result == None
    assert bc.database.list_of('payments.PlanFinancing') == bc.format.to_dict(model.plan_financing)
    assert tasks.charge_plan_financing.delay.call_args_list == []


@pytest.mark.parametrize('delta, status, status_changed', [
    (-relativedelta(days=1, seconds=1), 'ACTIVE', True),
    (-relativedelta(days=1, seconds=1), 'ERROR', False),
    (-relativedelta(days=1, seconds=1), 'PAYMENT_ISSUE', False),
])
def test_with_two_plan_financings__expired(bc: Breathecode, delta, status, status_changed, utc_now):
    valid_until = utc_now + delta
    plan_financing = {
        'next_payment_at': valid_until,
        'valid_until': valid_until,
        'status': status,
        'monthly_price': (random.random() * 99) + 1,
        'plan_expires_at': UTC_NOW + relativedelta(months=random.randint(1, 12)),
    }

    model = bc.database.create(plan_financing=(2, plan_financing))

    command = Command()
    result = command.handle()

    assert result == None

    db = bc.format.to_dict(model.plan_financing)
    for i in range(len(db)):
        if status_changed:
            db[i]['status'] = 'EXPIRED'

    assert bc.database.list_of('payments.PlanFinancing') == db
    assert tasks.charge_plan_financing.delay.call_args_list == []


@pytest.mark.parametrize('delta, status', [
    (relativedelta(days=2, seconds=1), 'ACTIVE'),
    (relativedelta(days=2, seconds=1), 'ERROR'),
    (relativedelta(days=2, seconds=1), 'PAYMENT_ISSUE'),
])
def test_with_two_plan_financings__valid_cases(bc: Breathecode, delta, status, utc_now):
    valid_until = utc_now + delta
    next_payment_at = utc_now - delta
    plan_financing = {
        'next_payment_at': next_payment_at,
        'valid_until': valid_until,
        'status': status,
        'monthly_price': (random.random() * 99) + 1,
        'plan_expires_at': UTC_NOW + relativedelta(months=random.randint(1, 12)),
    }

    model = bc.database.create(plan_financing=(2, plan_financing))

    command = Command()
    result = command.handle()

    assert result == None
    assert bc.database.list_of('payments.PlanFinancing') == bc.format.to_dict(model.plan_financing)
    assert tasks.charge_plan_financing.delay.call_args_list == [
        call(model.plan_financing[0].id),
        call(model.plan_financing[1].id),
    ]

from datetime import timedelta
from unittest.mock import MagicMock, call

import pytest
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.management.commands.retry_pending_bags import Command
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def apply_patch(db, monkeypatch: pytest.MonkeyPatch):
    m1 = MagicMock()
    m2 = MagicMock()
    m3 = MagicMock()

    monkeypatch.setattr(tasks.build_plan_financing, "delay", m1)
    monkeypatch.setattr(tasks.build_subscription, "delay", m2)
    monkeypatch.setattr(tasks.build_free_subscription, "delay", m3)

    yield m1, m2, m3


@pytest.mark.parametrize(
    "bags, in_the_past",
    [
        (0, False),
        (
            (
                2,
                {
                    "was_delivered": True,
                    "status": "RENEWAL",
                },
            ),
            False,
        ),
        (
            (
                2,
                {
                    "was_delivered": True,
                    "status": "CHECKING",
                },
            ),
            False,
        ),
        (
            (
                2,
                {
                    "was_delivered": True,
                    "status": "PAID",
                },
            ),
            False,
        ),
        (
            (
                2,
                {
                    "was_delivered": False,
                    "status": "RENEWAL",
                },
            ),
            True,
        ),
        (
            (
                2,
                {
                    "was_delivered": False,
                    "status": "CHECKING",
                },
            ),
            True,
        ),
        (
            (
                2,
                {
                    "was_delivered": False,
                    "status": "RENEWAL",
                },
            ),
            False,
        ),
        (
            (
                2,
                {
                    "was_delivered": False,
                    "status": "CHECKING",
                },
            ),
            False,
        ),
    ],
)
def test_nothing_to_process(bc: Breathecode, bags, in_the_past, utc_now, set_datetime):
    model = bc.database.create(bag=bags)
    if in_the_past:
        set_datetime(utc_now + timedelta(minutes=11))

    command = Command()
    result = command.handle()

    assert result == None

    db = []
    if bags:
        db = bc.format.to_dict(model.bag)
    assert bc.database.list_of("payments.Bag") == db

    assert tasks.build_plan_financing.delay.call_args_list == []
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []


@pytest.mark.parametrize(
    "bags, invoices, type",
    [
        (
            (
                2,
                {
                    "was_delivered": False,
                    "status": "PAID",
                    "how_many_installments": 0,
                },
            ),
            {
                "amount": 0,
            },
            "free",
        ),
        (
            (
                2,
                {
                    "was_delivered": False,
                    "status": "PAID",
                    "how_many_installments": 2,
                },
            ),
            {
                "amount": 0,
            },
            "financing",
        ),
        (
            (
                2,
                {
                    "was_delivered": False,
                    "status": "PAID",
                    "how_many_installments": 0,
                },
            ),
            {
                "amount": 2,
            },
            "subscription",
        ),
    ],
)
def test_rescheduling_bags(bc: Breathecode, bags, invoices, type, utc_now, set_datetime):
    model = bc.database.create(bag=bags, invoice=invoices)
    set_datetime(utc_now + timedelta(minutes=11))

    command = Command()
    result = command.handle()

    assert result == None

    db = bc.format.to_dict(model.bag)
    assert bc.database.list_of("payments.Bag") == db

    if type == "free":
        assert tasks.build_plan_financing.delay.call_args_list == []
        assert tasks.build_subscription.delay.call_args_list == []
        assert tasks.build_free_subscription.delay.call_args_list == [call(1, 1)]

    elif type == "financing":
        assert tasks.build_plan_financing.delay.call_args_list == [call(1, 1)]
        assert tasks.build_subscription.delay.call_args_list == []
        assert tasks.build_free_subscription.delay.call_args_list == []

    elif type == "subscription":
        assert tasks.build_plan_financing.delay.call_args_list == []
        assert tasks.build_subscription.delay.call_args_list == [call(1, 1)]
        assert tasks.build_free_subscription.delay.call_args_list == []

    else:
        assert 0, "type value is mandatory"


def test_invited_financing_retry_defaults_created_by_admin_false_without_invite(
    bc: Breathecode, utc_now, set_datetime
):
    bc.database.create(
        bag={
            "was_delivered": False,
            "status": "PAID",
            "how_many_installments": 2,
            "type": "INVITED",
        },
        invoice={"amount": 1},
    )
    set_datetime(utc_now + timedelta(minutes=11))

    Command().handle()

    assert tasks.build_plan_financing.delay.call_args_list == [call(1, 1, created_by_admin=False)]
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []


def test_invited_financing_retry_reads_created_by_admin_from_invite(bc: Breathecode, utc_now, set_datetime):
    model = bc.database.create(
        bag={
            "was_delivered": False,
            "status": "PAID",
            "how_many_installments": 2,
            "type": "INVITED",
        },
        invoice={"amount": 1},
        user_invite={"created_by_admin": True},
    )
    invite = model.user_invite
    invite.user = model.user
    invite.academy = model.academy
    invite.email = model.user.email
    invite.save()
    set_datetime(utc_now + timedelta(minutes=11))

    Command().handle()

    assert tasks.build_plan_financing.delay.call_args_list == [call(1, 1, created_by_admin=True)]
    assert tasks.build_subscription.delay.call_args_list == []
    assert tasks.build_free_subscription.delay.call_args_list == []

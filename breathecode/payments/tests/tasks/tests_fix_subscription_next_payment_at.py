"""
Test /answer
"""

import random
from datetime import timedelta
from logging import Logger
from unittest.mock import MagicMock, call

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.tests.mixins.breathecode_mixin import Breathecode

UTC_NOW = timezone.now()

# enable this file to use the database
pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    # mock logger with monkeypatch

    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())

    yield


@pytest.fixture
def reset_mock_calls():

    def wrapper():
        Logger.info.call_args_list = []
        Logger.error.call_args_list = []

    yield wrapper


@pytest.mark.parametrize("subscription_number", [0, 1])
def test_subscription_not_found(bc: Breathecode, reset_mock_calls, subscription_number, utc_now):
    if subscription_number:
        model = bc.database.create(
            subscription=(subscription_number, {"paid_at": utc_now, "next_payment_at": utc_now + timedelta(days=2)})
        )
        reset_mock_calls()

    tasks.fix_subscription_next_payment_at(1)

    assert bc.database.list_of("payments.CohortSet") == []
    assert bc.database.list_of("payments.CohortSetCohort") == []

    if subscription_number:
        assert bc.database.list_of("payments.Subscription") == [bc.format.to_dict(model.subscription)]

    else:
        assert bc.database.list_of("payments.Subscription") == []

    assert Logger.info.call_args_list == [
        call("Starting fix_subscription_next_payment_at for subscription 1"),
    ]
    assert Logger.error.call_args_list == [call("Subscription with id 1 not found", exc_info=True)]


@pytest.mark.parametrize(
    "pay_every, pay_every_unit, next_payment_at_delta",
    [
        (1, "DAY", relativedelta(days=1)),
        (3, "DAY", relativedelta(days=3)),
        (1, "WEEK", relativedelta(weeks=1)),
        (3, "WEEK", relativedelta(weeks=3)),
        (1, "MONTH", relativedelta(months=1)),
        (3, "MONTH", relativedelta(months=3)),
        (1, "YEAR", relativedelta(years=1)),
        (3, "YEAR", relativedelta(years=3)),
    ],
)
@pytest.mark.parametrize(
    "delta",
    [-timedelta(days=2), -timedelta(days=1), timedelta(days=0), timedelta(days=1), timedelta(days=2)],
)
def test_fix_payment_at_for_subscription(
    bc: Breathecode, reset_mock_calls, utc_now, delta, pay_every, pay_every_unit, next_payment_at_delta
):
    model = bc.database.create(
        subscription=(
            {
                "paid_at": utc_now + delta,
                "next_payment_at": utc_now + delta,
                "pay_every": pay_every,
                "pay_every_unit": pay_every_unit,
            }
        )
    )
    reset_mock_calls()

    tasks.fix_subscription_next_payment_at(1)

    assert bc.database.list_of("payments.CohortSet") == []
    assert bc.database.list_of("payments.CohortSetCohort") == []

    assert bc.database.list_of("payments.Subscription") == [
        {**bc.format.to_dict(model.subscription), "next_payment_at": utc_now + delta + next_payment_at_delta}
    ]

    assert Logger.info.call_args_list == [
        call("Starting fix_subscription_next_payment_at for subscription 1"),
    ]
    assert Logger.error.call_args_list == []

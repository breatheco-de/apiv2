"""
Test /answer
"""

import random
from logging import Logger
from unittest.mock import MagicMock, call

import pytest
from django.utils import timezone
from task_manager.core.exceptions import AbortTask

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


# When: subscription not found
# Then: should abort the execution
def test_subscription_set_not_found(bc: Breathecode, reset_mock_calls):

    if have_subscription := random.randint(0, 1):
        subscription = {"status": random.choice(["CANCELLED", "DEPRECATED"])}
        model = bc.database.create(subscription=subscription)
        reset_mock_calls()

    tasks.add_cohort_set_to_subscription(1, 1)

    assert bc.database.list_of("payments.CohortSet") == []
    assert bc.database.list_of("payments.CohortSetCohort") == []

    if have_subscription:
        assert bc.database.list_of("payments.Subscription") == [bc.format.to_dict(model.subscription)]

    else:
        assert bc.database.list_of("payments.Subscription") == []

    assert Logger.info.call_args_list == [
        call("Starting add_cohort_set_to_subscription for subscription 1 cohort_set 1"),
        # retry
        call("Starting add_cohort_set_to_subscription for subscription 1 cohort_set 1"),
    ]
    assert Logger.error.call_args_list == [call("Subscription with id 1 not found", exc_info=True)]


# When: cohort set not found
# Then: should abort the execution
def test_cohort_set_not_found(bc: Breathecode, reset_mock_calls):

    model = bc.database.create(subscription=1)
    reset_mock_calls()

    tasks.add_cohort_set_to_subscription(1, 1)

    assert bc.database.list_of("payments.CohortSet") == []
    assert bc.database.list_of("payments.CohortSetCohort") == []
    assert bc.database.list_of("payments.Subscription") == [bc.format.to_dict(model.subscription)]

    assert Logger.info.call_args_list == [
        call("Starting add_cohort_set_to_subscription for subscription 1 cohort_set 1"),
        # retry
        call("Starting add_cohort_set_to_subscription for subscription 1 cohort_set 1"),
    ]
    assert Logger.error.call_args_list == [call("CohortSet with id 1 not found", exc_info=True)]


# When: subscription is over
# Then: should abort the execution
def test_subscription_is_over(bc: Breathecode, reset_mock_calls):

    academy = {"available_as_saas": True}
    subscription = {"valid_until": timezone.now() - timezone.timedelta(days=random.randint(1, 1000))}
    model = bc.database.create(subscription=subscription, cohort_set=1, academy=academy)
    reset_mock_calls()

    tasks.add_cohort_set_to_subscription(1, 1)

    assert bc.database.list_of("payments.CohortSet") == [bc.format.to_dict(model.cohort_set)]
    assert bc.database.list_of("payments.CohortSetCohort") == []
    assert bc.database.list_of("payments.Subscription") == [bc.format.to_dict(model.subscription)]

    assert Logger.info.call_args_list == [
        call("Starting add_cohort_set_to_subscription for subscription 1 cohort_set 1"),
    ]
    assert Logger.error.call_args_list == [call("The subscription 1 is over", exc_info=True)]


# When: subscription with selected_cohort_set
# Then: should abort the execution
def test_subscription_have_a_cohort_set(bc: Breathecode, reset_mock_calls, caplog):

    academy = {"available_as_saas": True}
    subscription = {"valid_until": timezone.now() + timezone.timedelta(days=random.randint(1, 1000))}
    model = bc.database.create(subscription=subscription, cohort_set=1, academy=academy)
    reset_mock_calls()

    tasks.add_cohort_set_to_subscription(1, 1)

    assert bc.database.list_of("payments.CohortSet") == [bc.format.to_dict(model.cohort_set)]
    assert bc.database.list_of("payments.CohortSetCohort") == []
    assert bc.database.list_of("payments.Subscription") == [bc.format.to_dict(model.subscription)]

    assert Logger.info.call_args_list == [
        call("Starting add_cohort_set_to_subscription for subscription 1 cohort_set 1"),
    ]
    assert Logger.error.call_args_list == [call("Subscription with id 1 already have a cohort set", exc_info=True)]


# When: all is ok
# Then: should add the cohort set to the subscription
def test_all_is_ok(bc: Breathecode, reset_mock_calls):

    academy = {"available_as_saas": True}
    subscription = {
        "valid_until": timezone.now() + timezone.timedelta(days=random.randint(1, 1000)),
        "selected_cohort_set_id": None,
    }
    model = bc.database.create(subscription=subscription, cohort_set=1, academy=academy)
    reset_mock_calls()

    tasks.add_cohort_set_to_subscription(1, 1)

    assert bc.database.list_of("payments.CohortSet") == [bc.format.to_dict(model.cohort_set)]
    assert bc.database.list_of("payments.CohortSetCohort") == []
    assert bc.database.list_of("payments.Subscription") == [
        {
            **bc.format.to_dict(model.subscription),
            "selected_cohort_set_id": 1,
        },
    ]

    assert Logger.info.call_args_list == [
        call("Starting add_cohort_set_to_subscription for subscription 1 cohort_set 1"),
    ]
    assert Logger.error.call_args_list == []

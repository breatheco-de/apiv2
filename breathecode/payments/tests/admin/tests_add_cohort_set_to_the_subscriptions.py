"""
Test /answer
"""

from django import forms
import random
import pytest
from unittest.mock import MagicMock, call
from breathecode.payments import tasks

from django.utils import timezone
from breathecode.payments.admin import add_cohort_set_to_the_subscriptions
from breathecode.tests.mixins.breathecode_mixin import Breathecode

UTC_NOW = timezone.now()

# enable this file to use the database
pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr("breathecode.payments.tasks.add_cohort_set_to_subscription.delay", MagicMock())

    yield


# When: no cohort sets
# Then: shouldn't to do anything
def test_no_cohort_sets(bc: Breathecode):

    CohortSet = bc.database.get_model("payments.CohortSet")
    queryset = CohortSet.objects.all()

    add_cohort_set_to_the_subscriptions(None, None, queryset)

    assert bc.database.list_of("payments.CohortSet") == []
    assert bc.database.list_of("payments.CohortSetCohort") == []
    assert bc.database.list_of("payments.Subscription") == []

    assert tasks.add_cohort_set_to_subscription.delay.call_args_list == []


# When: two cohort sets
# Then: raise an error
def test_two_cohort_sets(bc: Breathecode):
    # with pytest.raises(forms.ValidationError, match='academy-not-available-as-saas'):
    if random.randint(0, 1):
        academy = {"available_as_saas": True}
        cohort = {"available_as_saas": None}
    else:
        academy = {"available_as_saas": True}
        cohort = {"available_as_saas": True}

    cohort_set_cohorts = [{"cohort_id": x + 1} for x in range(2)]

    model = bc.database.create(cohort=(2, cohort), academy=academy, cohort_set=2, cohort_set_cohort=cohort_set_cohorts)

    CohortSet = bc.database.get_model("payments.CohortSet")
    queryset = CohortSet.objects.all()

    with pytest.raises(forms.ValidationError, match="You just can select one subscription at a time"):
        add_cohort_set_to_the_subscriptions(None, None, queryset)

    assert bc.database.list_of("payments.CohortSet") == bc.format.to_dict(model.cohort_set)
    assert bc.database.list_of("payments.CohortSetCohort") == bc.format.to_dict(model.cohort_set_cohort)
    assert bc.database.list_of("payments.Subscription") == []

    assert tasks.add_cohort_set_to_subscription.delay.call_args_list == []


# When: one cohort set, no subscriptions
# Then: shouldn't to do anything
def test_one_cohort_set(bc: Breathecode):
    # with pytest.raises(forms.ValidationError, match='academy-not-available-as-saas'):
    if random.randint(0, 1):
        academy = {"available_as_saas": True}
        cohort = {"available_as_saas": None}
    else:
        academy = {"available_as_saas": True}
        cohort = {"available_as_saas": True}

    model = bc.database.create(cohort=cohort, academy=academy, cohort_set=1, cohort_set_cohort=1)

    CohortSet = bc.database.get_model("payments.CohortSet")
    queryset = CohortSet.objects.all()

    add_cohort_set_to_the_subscriptions(None, None, queryset)

    assert bc.database.list_of("payments.CohortSet") == [bc.format.to_dict(model.cohort_set)]
    assert bc.database.list_of("payments.CohortSetCohort") == [bc.format.to_dict(model.cohort_set_cohort)]
    assert bc.database.list_of("payments.Subscription") == []

    assert tasks.add_cohort_set_to_subscription.delay.call_args_list == []


# When: one cohort set, two subscriptions
# Then: run tasks to add cohort set to the subscriptions
def test_one_cohort_set__two_subscriptions(bc: Breathecode):
    # with pytest.raises(forms.ValidationError, match='academy-not-available-as-saas'):
    if random.randint(0, 1):
        academy = {"available_as_saas": True}
        cohort = {"available_as_saas": None}
    else:
        academy = {"available_as_saas": True}
        cohort = {"available_as_saas": True}

    subscriptions = [{"selected_cohort_set_id": None} for _ in range(2)]

    model = bc.database.create(
        cohort=cohort, academy=academy, cohort_set=1, cohort_set_cohort=1, subscription=subscriptions
    )

    CohortSet = bc.database.get_model("payments.CohortSet")
    queryset = CohortSet.objects.all()

    add_cohort_set_to_the_subscriptions(None, None, queryset)

    assert bc.database.list_of("payments.CohortSet") == [bc.format.to_dict(model.cohort_set)]
    assert bc.database.list_of("payments.CohortSetCohort") == [bc.format.to_dict(model.cohort_set_cohort)]
    assert bc.database.list_of("payments.Subscription") == bc.format.to_dict(model.subscription)

    assert tasks.add_cohort_set_to_subscription.delay.call_args_list == [call(1, 1), call(2, 1)]


# When: one cohort set, two subscriptions with selected_cohort_set
# Then: shouldn't to schedule any task
def test_one_cohort_set__two_subscriptions__cohort_set_already_selected(bc: Breathecode):
    # with pytest.raises(forms.ValidationError, match='academy-not-available-as-saas'):
    if random.randint(0, 1):
        academy = {"available_as_saas": True}
        cohort = {"available_as_saas": None}
    else:
        academy = {"available_as_saas": True}
        cohort = {"available_as_saas": True}

    subscriptions = [{"selected_cohort_set_id": 1} for _ in range(2)]

    model = bc.database.create(
        cohort=cohort, academy=academy, cohort_set=1, cohort_set_cohort=1, subscription=subscriptions
    )

    CohortSet = bc.database.get_model("payments.CohortSet")
    queryset = CohortSet.objects.all()

    add_cohort_set_to_the_subscriptions(None, None, queryset)

    assert bc.database.list_of("payments.CohortSet") == [bc.format.to_dict(model.cohort_set)]
    assert bc.database.list_of("payments.CohortSetCohort") == [bc.format.to_dict(model.cohort_set_cohort)]
    assert bc.database.list_of("payments.Subscription") == [
        {
            **bc.format.to_dict(model.subscription)[n - 1],
            "selected_cohort_set_id": 1,
        }
        for n in range(1, 3)
    ]

    assert tasks.add_cohort_set_to_subscription.delay.call_args_list == []

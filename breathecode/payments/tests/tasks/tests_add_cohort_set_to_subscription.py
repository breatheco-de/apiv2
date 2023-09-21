"""
Test /answer
"""
import random
import pytest
from breathecode.payments import tasks

from django.utils import timezone
from breathecode.tests.mixins.breathecode_mixin import Breathecode
from breathecode.utils.decorators.task import AbortTask

UTC_NOW = timezone.now()

# enable this file to use the database
pytestmark = pytest.mark.usefixtures('db')


# When: subscription not found
# Then: should abort the execution
def test_subscription_set_not_found(bc: Breathecode):

    if have_subscription := random.randint(0, 1):
        subscription = {'status': random.choice(['CANCELLED', 'DEPRECATED'])}
        model = bc.database.create(subscription=subscription)

    with pytest.raises(AbortTask, match='Subscription with id 1 not found'):
        tasks.add_cohort_set_to_subscription(1, 1)

    assert bc.database.list_of('payments.CohortSet') == []
    assert bc.database.list_of('payments.CohortSetCohort') == []

    if have_subscription:
        assert bc.database.list_of('payments.Subscription') == [bc.format.to_dict(model.subscription)]

    else:
        assert bc.database.list_of('payments.Subscription') == []


# When: cohort set not found
# Then: should abort the execution
def test_cohort_set_not_found(bc: Breathecode):

    model = bc.database.create(subscription=1)

    with pytest.raises(AbortTask, match='CohortSet with id 1 not found'):
        tasks.add_cohort_set_to_subscription(1, 1)

    assert bc.database.list_of('payments.CohortSet') == []
    assert bc.database.list_of('payments.CohortSetCohort') == []
    assert bc.database.list_of('payments.Subscription') == [bc.format.to_dict(model.subscription)]


# When: subscription is over
# Then: should abort the execution
def test_subscription_is_over(bc: Breathecode):

    academy = {'available_as_saas': True}
    subscription = {'valid_until': timezone.now() - timezone.timedelta(days=random.randint(1, 1000))}
    model = bc.database.create(subscription=subscription, cohort_set=1, academy=academy)

    with pytest.raises(AbortTask, match='The subscription 1 is over'):
        tasks.add_cohort_set_to_subscription(1, 1)

    assert bc.database.list_of('payments.CohortSet') == [bc.format.to_dict(model.cohort_set)]
    assert bc.database.list_of('payments.CohortSetCohort') == []
    assert bc.database.list_of('payments.Subscription') == [bc.format.to_dict(model.subscription)]


# When: subscription with selected_cohort_set
# Then: should abort the execution
def test_subscription_have_a_cohort_set(bc: Breathecode):

    academy = {'available_as_saas': True}
    subscription = {'valid_until': timezone.now() + timezone.timedelta(days=random.randint(1, 1000))}
    model = bc.database.create(subscription=subscription, cohort_set=1, academy=academy)

    with pytest.raises(AbortTask, match='Subscription with id 1 already have a cohort set'):
        tasks.add_cohort_set_to_subscription(1, 1)

    assert bc.database.list_of('payments.CohortSet') == [bc.format.to_dict(model.cohort_set)]
    assert bc.database.list_of('payments.CohortSetCohort') == []
    assert bc.database.list_of('payments.Subscription') == [bc.format.to_dict(model.subscription)]


# When: all is ok
# Then: should add the cohort set to the subscription
def test_all_is_ok(bc: Breathecode):

    academy = {'available_as_saas': True}
    subscription = {
        'valid_until': timezone.now() + timezone.timedelta(days=random.randint(1, 1000)),
        'selected_cohort_set_id': None,
    }
    model = bc.database.create(subscription=subscription, cohort_set=1, academy=academy)

    tasks.add_cohort_set_to_subscription(1, 1)

    assert bc.database.list_of('payments.CohortSet') == [bc.format.to_dict(model.cohort_set)]
    assert bc.database.list_of('payments.CohortSetCohort') == []
    assert bc.database.list_of('payments.Subscription') == [
        {
            **bc.format.to_dict(model.subscription),
            'selected_cohort_set_id': 1,
        },
    ]

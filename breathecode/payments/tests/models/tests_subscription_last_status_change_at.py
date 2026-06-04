import pytest

from breathecode.payments.models import Subscription


@pytest.mark.django_db
def test_last_status_change_at_set_on_create(database):
    model = database.create(subscription=1)
    subscription = model.subscription

    assert subscription.last_status_change_at is not None


@pytest.mark.django_db
def test_last_status_change_at_updates_when_status_changes(database):
    model = database.create(subscription=1)
    subscription = model.subscription
    first_change = subscription.last_status_change_at

    subscription.status = Subscription.Status.CANCELLED
    subscription.save()
    subscription.refresh_from_db()

    assert subscription.last_status_change_at is not None
    assert subscription.last_status_change_at >= first_change


@pytest.mark.django_db
def test_last_status_change_at_unchanged_when_status_same(database):
    model = database.create(subscription=1)
    subscription = model.subscription
    previous = subscription.last_status_change_at

    subscription.status_message = "No status change"
    subscription.save()
    subscription.refresh_from_db()

    assert subscription.last_status_change_at == previous

import pytest
from unittest.mock import MagicMock

from django.utils import timezone
from breathecode.payments import signals


@pytest.fixture(autouse=True)
def auto_enable_signals(enable_signals):
    enable_signals()
    yield


def _build_service_with_group(database):
    # Create a group and a service bound to it
    group = database.create(group=1).group
    service = database.create(service=1).service
    service.groups.add(group)
    service_item = database.create(service_item={"service_id": service.id, "how_many": 5}).service_item
    return group, service, service_item


def _build_subscription_with_seat(database):
    model = database.create(country=1, city=1, academy=1, currency=1, subscription=1)
    subscription = model.subscription

    # Create team and seat user
    team = database.create(
        subscription_billing_team={"subscription_id": subscription.id}, country=1, city=1
    ).subscription_billing_team
    seat_user = database.create(user=1).user

    seat = database.create(
        subscription_seat={
            "billing_team_id": team.id,
            "user_id": seat_user.id,
            "email": seat_user.email,
            "is_active": True,
            "seat_multiplier": 1,
        }
    ).subscription_seat

    return subscription, seat, seat_user


def test_grant_permissions_applies_to_seat_user(database):
    group, service, service_item = _build_service_with_group(database)
    subscription, seat, seat_user = _build_subscription_with_seat(database)

    # Create consumable for the seat; signal on save should grant permissions to seat user
    consumable = database.create(
        consumable={
            "service_item_id": service_item.id,
            "subscription_id": subscription.id,
            "subscription_seat_id": seat.id,
            "user_id": subscription.user_id,  # owner; should NOT receive groups for seat consumable
            "how_many": 5,
            "valid_until": None,
        }
    ).consumable

    # group must be granted to seat user only
    seat_user.refresh_from_db()
    subscription.user.refresh_from_db()

    assert list(seat_user.groups.values_list("id", flat=True)) == [group.id]
    assert list(subscription.user.groups.values_list("id", flat=True)) == []


def test_lose_permissions_removes_from_seat_user(database):
    group, service, service_item = _build_service_with_group(database)
    subscription, seat, seat_user = _build_subscription_with_seat(database)

    # Grant by creating a consumable
    consumable = database.create(
        consumable={
            "service_item_id": service_item.id,
            "subscription_id": subscription.id,
            "subscription_seat_id": seat.id,
            "user_id": subscription.user_id,
            "how_many": 1,
            "valid_until": None,
        }
    ).consumable

    # Ensure group is there
    seat_user.refresh_from_db()
    assert list(seat_user.groups.values_list("id", flat=True)) == [group.id]

    # Consume to zero and trigger lose permissions
    consumable.how_many = 0
    consumable.save()

    signals.lose_service_permissions.send(sender=consumable.__class__, instance=consumable)

    seat_user.refresh_from_db()
    assert list(seat_user.groups.values_list("id", flat=True)) == []

"""Unit and integration tests for grant_plan_permissions_receiver.

These tests cover:
- Subscription with team: grants Paid Student to each seat user.
- PlanFinancing: grants Paid Student to the owner user.
- Group not found: nothing happens.
- DB integration: real user gets added to Paid Student group.
"""

from unittest.mock import MagicMock, patch

import pytest


def make_user():
    """Build a MagicMock user without Paid Student membership by default."""
    user = MagicMock()
    # user.groups.filter(name=...).exists()
    user.groups.filter.return_value.exists.return_value = False
    return user


def make_group(name="Paid Student"):
    """Build a MagicMock Group with the provided name (defaults to Paid Student)."""
    g = MagicMock()
    g.name = name
    return g


def make_subscription_instance(user=None):
    """Build a Subscription-like MagicMock instance with a user attribute."""
    inst = MagicMock()
    if user is None:
        user = make_user()
    inst.user = user
    return inst


def make_plan_financing_instance(user=None):
    """Build a PlanFinancing-like MagicMock instance with a user attribute."""
    inst = MagicMock()
    if user is None:
        user = make_user()
    inst.user = user
    return inst


@patch("breathecode.payments.receivers.SubscriptionBillingTeam")
@patch("breathecode.payments.receivers.Group")
def test_grant_subscription_with_team_adds_paid_student_to_each_seat_user(
    mock_group, mock_team, monkeypatch: pytest.MonkeyPatch
):
    """
    Given a subscription that has a billing team with two seat users
    When grant_plan_permissions_receiver is invoked for that subscription
    Then each seat user is granted membership to the Paid Student group.
    """
    from breathecode.payments.receivers import grant_plan_permissions_receiver

    # Arrange
    group = make_group()
    mock_group.objects.filter.return_value.first.return_value = group

    seat_user_1 = make_user()
    seat_user_2 = make_user()

    seat1 = MagicMock()
    seat1.user = seat_user_1

    seat2 = MagicMock()
    seat2.user = seat_user_2

    team = MagicMock()
    team.subscription_seat_set.all.return_value = [seat1, seat2]
    mock_team.objects.filter.return_value.first.return_value = team

    # Patch Subscription class in receivers to a simple dummy class so isinstance checks pass
    class DummySubscription:
        pass

    monkeypatch.setattr("breathecode.payments.receivers.Subscription", DummySubscription, raising=True)
    subscription = DummySubscription()

    # Act
    grant_plan_permissions_receiver(sender=type(subscription), instance=subscription)

    # Assert
    assert seat_user_1.groups.add.called
    assert seat_user_2.groups.add.called
    # Ensure we looked up team by subscription
    mock_team.objects.filter.assert_called_once()


@patch("breathecode.payments.receivers.Group")
def test_grant_plan_financing_adds_group_to_owner_user(mock_group):
    """
    Given a PlanFinancing instance owned by a user
    When grant_plan_permissions_receiver is invoked for that instance
    Then the owner user is granted membership to the Paid Student group.
    """
    from breathecode.payments.receivers import grant_plan_permissions_receiver

    # Arrange
    group = make_group()
    mock_group.objects.filter.return_value.first.return_value = group

    pf = make_plan_financing_instance()

    # Act
    grant_plan_permissions_receiver(sender=type(pf), instance=pf)

    # Assert
    assert pf.user.groups.add.called


@patch("breathecode.payments.receivers.Group")
def test_grant_ignores_when_group_not_found(mock_group):
    """
    Given the Paid Student group does not exist in the system
    When grant_plan_permissions_receiver is invoked
    Then no group addition should occur for the user.
    """
    from breathecode.payments.receivers import grant_plan_permissions_receiver

    # Arrange
    mock_group.objects.filter.return_value.first.return_value = None
    subscription = make_subscription_instance()

    # Act
    grant_plan_permissions_receiver(sender=type(subscription), instance=subscription)

    # Assert
    assert subscription.user.groups.add.called is False


@pytest.mark.django_db
def test_grant_integration_adds_paid_student_group_to_real_user(database):
    """
    Integration test
    Given a real User and an existing Paid Student group in the DB
    When grant_plan_permissions_receiver is invoked for a subscription-like instance
    Then the user becomes a member of the Paid Student group (verified via ORM).
    """
    from django.contrib.auth.models import Group, User
    from breathecode.payments.receivers import grant_plan_permissions_receiver

    # Arrange (real DB for User/Group, mocked SubscriptionBillingTeam lookup not used)
    user = User.objects.create(username="john", email="john@example.com")
    Group.objects.get_or_create(name="Paid Student")

    instance = make_subscription_instance(user=user)

    # Act
    grant_plan_permissions_receiver(sender=type(instance), instance=instance)

    # Assert (real DB membership)
    assert user.groups.filter(name="Paid Student").exists()

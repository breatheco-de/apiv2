"""Unit tests for revoke_plan_permissions_receiver.

These tests validate:
- Removal of Paid Student when the user has no other active paid plans.
- No removal when the user still has other active paid plans.
- No-op if the Paid Student group is not present or the user is not in that group.
- Team path iterates seats but current implementation removes only the owner membership.
"""

from unittest.mock import MagicMock, patch
import pytest


def make_user(in_group=True):
    """Build a MagicMock user with membership toggle for Paid Student group."""
    user = MagicMock()
    # membership checks
    user.groups.filter.return_value.exists.return_value = in_group
    return user


def make_group(name="Paid Student"):
    """Build a MagicMock Group named Paid Student by default."""
    g = MagicMock()
    g.name = name
    return g


def make_subscription_instance(user=None):
    """Build a Subscription-like MagicMock with user attribute."""
    inst = MagicMock()
    if user is None:
        user = make_user()
    inst.user = user
    return inst


def make_plan_financing_instance(user=None):
    """Build a PlanFinancing-like MagicMock with user attribute."""
    inst = MagicMock()
    if user is None:
        user = make_user()
    inst.user = user
    return inst


@patch("breathecode.payments.actions.user_has_active_paid_plans", return_value=False)
@patch("breathecode.payments.receivers.Group")
def test_revoke_subscription_with_no_team_removes_group_when_no_other_paid_plans(
    mock_group, mock_has_active_paid_plans
):
    """
    Given a subscription owner in Paid Student with no other active paid plans
    When revoke_plan_permissions_receiver is invoked for that subscription
    Then the user is removed from the Paid Student group and the active-plans check is called.
    """
    from breathecode.payments.receivers import revoke_plan_permissions_receiver

    # Arrange
    group = make_group()
    mock_group.objects.filter.return_value.first.return_value = group
    user = make_user(in_group=True)
    subscription = make_subscription_instance(user=user)

    # Act
    revoke_plan_permissions_receiver(sender=type(subscription), instance=subscription)

    # Assert
    user.groups.remove.assert_called_once_with(group)
    mock_has_active_paid_plans.assert_called_once_with(user)


@patch("breathecode.payments.actions.user_has_active_paid_plans", return_value=True)
@patch("breathecode.payments.receivers.Group")
def test_revoke_ignored_when_user_has_other_paid_plans(mock_group, mock_has_active_paid_plans):
    """
    Given a subscription owner in Paid Student with other active paid plans
    When revoke_plan_permissions_receiver is invoked
    Then the group is not removed and the active-plans check is called.
    """
    from breathecode.payments.receivers import revoke_plan_permissions_receiver

    # Arrange
    group = make_group()
    mock_group.objects.filter.return_value.first.return_value = group
    user = make_user(in_group=True)
    subscription = make_subscription_instance(user=user)

    # Act
    revoke_plan_permissions_receiver(sender=type(subscription), instance=subscription)

    # Assert
    assert user.groups.remove.called is False
    mock_has_active_paid_plans.assert_called_once_with(user)


@patch("breathecode.payments.actions.user_has_active_paid_plans", return_value=False)
@patch("breathecode.payments.receivers.Group")
def test_revoke_ignored_when_group_not_found(mock_group, mock_has_active_paid_plans):
    """
    Given the Paid Student group does not exist
    When revoke_plan_permissions_receiver is invoked
    Then no removal occurs and the active-plans helper is not called.
    """
    from breathecode.payments.receivers import revoke_plan_permissions_receiver

    # Arrange
    mock_group.objects.filter.return_value.first.return_value = None
    user = make_user(in_group=True)
    subscription = make_subscription_instance(user=user)

    # Act
    revoke_plan_permissions_receiver(sender=type(subscription), instance=subscription)

    # Assert
    assert user.groups.remove.called is False
    assert mock_has_active_paid_plans.called is False


@patch("breathecode.payments.actions.user_has_active_paid_plans", return_value=False)
@patch("breathecode.payments.receivers.Group")
def test_revoke_ignored_when_user_not_in_group(mock_group, mock_has_active_paid_plans):
    """
    Given a subscription owner that is not in the Paid Student group
    When revoke_plan_permissions_receiver is invoked
    Then it should no-op and not call the active-plans helper.
    """
    from breathecode.payments.receivers import revoke_plan_permissions_receiver

    # Arrange
    group = make_group()
    mock_group.objects.filter.return_value.first.return_value = group
    user = make_user(in_group=False)
    subscription = make_subscription_instance(user=user)

    # Act
    revoke_plan_permissions_receiver(sender=type(subscription), instance=subscription)

    # Assert
    assert user.groups.remove.called is False
    assert mock_has_active_paid_plans.called is False


@patch("breathecode.payments.actions.user_has_active_paid_plans", return_value=False)
@patch("breathecode.payments.receivers.SubscriptionBillingTeam")
@patch("breathecode.payments.receivers.Group")
def test_revoke_subscription_with_team_calls_team_iteration_and_removes_owner_only(
    mock_group, mock_team, mock_has_active_paid_plans, monkeypatch
):
    """
    Current behavior: inside revoke(user) the function uses instance.user instead of the passed user.
    Ensure team seat iteration happens and only the owner user is affected.
    """
    from breathecode.payments.receivers import revoke_plan_permissions_receiver

    # Arrange
    group = make_group()
    mock_group.objects.filter.return_value.first.return_value = group

    owner = make_user(in_group=True)
    seat_user_1 = make_user(in_group=True)
    seat_user_2 = make_user(in_group=True)

    seat1 = MagicMock()
    seat1.user = seat_user_1
    seat2 = MagicMock()
    seat2.user = seat_user_2

    team = MagicMock()
    team.subscription_seat_set.all.return_value = [seat1, seat2]
    mock_team.objects.filter.return_value.first.return_value = team

    # Patch Subscription to a dummy class so isinstance checks pass without Django FK constraints
    class DummySubscription:
        pass

    monkeypatch.setattr("breathecode.payments.receivers.Subscription", DummySubscription, raising=True)
    subscription = DummySubscription()
    subscription.user = owner

    # Act
    revoke_plan_permissions_receiver(sender=type(subscription), instance=subscription)

    # Assert: team iteration performed
    mock_team.objects.filter.assert_called_once()
    team.subscription_seat_set.all.assert_called_once()

    # Owner removal is performed once per seat iteration in current implementation (2 seats => 2 calls)
    assert owner.groups.remove.call_count == 2
    for args, kwargs in owner.groups.remove.call_args_list:
        assert args == (group,)
    assert seat_user_1.groups.remove.called is False
    assert seat_user_2.groups.remove.called is False
    # user_has_active_paid_plans called with owner per each seat iteration + owner path
    assert mock_has_active_paid_plans.call_count >= 1


@pytest.mark.django_db
@patch("breathecode.payments.actions.user_has_active_paid_plans", return_value=False)
def test_revoke_integration_removes_paid_student_group_from_real_user(mock_has_active_paid_plans, database):
    """
    Integration test
    Given a real User in the Paid Student group and no other active paid plans
    When revoke_plan_permissions_receiver is invoked for a subscription-like instance
    Then the user is removed from the Paid Student group (verified via ORM).
    """
    from django.contrib.auth.models import Group, User
    from breathecode.payments.receivers import revoke_plan_permissions_receiver

    # Arrange (real DB for User/Group)
    user = User.objects.create(username="alice", email="alice@example.com")
    group, _ = Group.objects.get_or_create(name="Paid Student")
    user.groups.add(group)

    # Subscription-like instance with real user attached
    instance = MagicMock()
    instance.user = user

    # Act
    revoke_plan_permissions_receiver(sender=type(instance), instance=instance)

    # Assert: membership removed and helper was consulted
    assert user.groups.filter(name="Paid Student").exists() is False
    mock_has_active_paid_plans.assert_called_once_with(user)

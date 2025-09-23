import pytest
from unittest.mock import MagicMock, patch


@patch("breathecode.payments.actions.invite_user_to_subscription_team")
@patch("breathecode.payments.actions.SubscriptionSeat")
def test_replace_seat_happy_path_updates_seat_and_invites_if_no_user(mock_seat_cls, mock_invite):
    """Replace updates email/user, logs action, saves and invites if to_user is None."""
    from breathecode.payments.actions import replace_seat

    seat_instance = MagicMock()
    seat_instance.seat_log = []
    mock_seat_cls.objects.filter.return_value.first.return_value = seat_instance

    mock_seat_cls.objects.filter.return_value.exists.return_value = False

    current_seat = MagicMock()
    current_seat.billing_team.subscription = MagicMock(id=44)
    current_seat.billing_team.consumption_strategy = "PER_SEAT"

    seat = replace_seat("old@example.com", "new@example.com", to_user=None, subscription_seat=current_seat, lang="en")

    assert seat is seat_instance
    assert seat_instance.email == "new@example.com"
    assert seat_instance.user is None
    assert seat_instance.is_active is True
    assert len(seat_instance.seat_log) == 1
    assert seat_instance.save.call_count >= 1
    mock_invite.assert_called_once()


@patch("breathecode.payments.actions.SubscriptionSeat")
def test_replace_seat_from_not_found_raises(mock_seat_cls):
    """Raises when seat with from_email is not found."""
    from breathecode.payments.actions import replace_seat, ValidationException

    mock_seat_cls.objects.filter.return_value.first.return_value = None

    current_seat = MagicMock()
    current_seat.billing_team = MagicMock()

    with pytest.raises(ValidationException):
        replace_seat("old@example.com", "new@example.com", to_user=None, subscription_seat=current_seat, lang="en")


@patch("breathecode.payments.actions.Consumable")
@patch("breathecode.payments.actions.invite_user_to_subscription_team")
@patch("breathecode.payments.actions.SubscriptionSeat")
def test_replace_seat_with_user_per_seat_reassigns_consumables(mock_seat_cls, mock_invite, mock_consumable):
    """When to_user is provided and strategy is PER_SEAT, do not invite and reassign consumables to new user."""
    from breathecode.payments.actions import replace_seat

    seat_instance = MagicMock()
    seat_instance.seat_log = []
    mock_seat_cls.objects.filter.return_value.first.return_value = seat_instance
    mock_seat_cls.objects.filter.return_value.exists.return_value = False

    current_seat = MagicMock()
    current_seat.billing_team.subscription = MagicMock(id=22)
    current_seat.billing_team.consumption_strategy = "PER_SEAT"

    new_user = MagicMock()

    seat = replace_seat(
        "old@example.com", "new@example.com", to_user=new_user, subscription_seat=current_seat, lang="en"
    )

    assert seat is seat_instance
    mock_invite.assert_not_called()
    mock_consumable.objects.filter.assert_called_once_with(subscription_seat=seat_instance)
    mock_consumable.objects.filter.return_value.update.assert_called_once_with(user=new_user)


@patch("breathecode.payments.actions.Consumable")
@patch("breathecode.payments.actions.SubscriptionSeat")
def test_replace_seat_per_team_does_not_reassign_consumables(mock_seat_cls, mock_consumable):
    """When strategy is PER_TEAM, do not reassign consumables."""
    from breathecode.payments.actions import replace_seat

    seat_instance = MagicMock()
    seat_instance.seat_log = []
    mock_seat_cls.objects.filter.return_value.first.return_value = seat_instance
    mock_seat_cls.objects.filter.return_value.exists.return_value = False

    current_seat = MagicMock()
    current_seat.billing_team.subscription = MagicMock(id=22)
    current_seat.billing_team.consumption_strategy = "PER_TEAM"

    new_user = MagicMock()

    replace_seat("old@example.com", "new@example.com", to_user=new_user, subscription_seat=current_seat, lang="en")

    mock_consumable.objects.filter.assert_not_called()


@patch("breathecode.payments.actions.SubscriptionSeat")
def test_replace_seat_to_email_exists_raises(mock_seat_cls):
    """Raises when a seat already exists with the to_email in the same team."""
    from breathecode.payments.actions import replace_seat, ValidationException

    mock_seat_cls.objects.filter.return_value.first.return_value = MagicMock(seat_log=[])
    mock_seat_cls.objects.filter.return_value.exists.return_value = True

    current_seat = MagicMock()
    current_seat.billing_team = MagicMock()

    with pytest.raises(ValidationException):
        replace_seat("old@example.com", "new@example.com", to_user=None, subscription_seat=current_seat, lang="en")

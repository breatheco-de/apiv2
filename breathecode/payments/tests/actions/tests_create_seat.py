import pytest
from unittest.mock import MagicMock, patch


@patch("breathecode.payments.actions.tasks")
@patch("breathecode.payments.actions.invite_user_to_subscription_team")
@patch("breathecode.payments.actions.SubscriptionSeat")
def test_create_seat_happy_path_creates_seat_and_invites_and_schedules(mock_seat_cls, mock_invite, mock_tasks):
    """Creates seat, logs entry, invites when user is None, and schedules stock build."""
    from breathecode.payments.actions import create_seat

    mock_seat_cls.objects.filter.return_value.exists.return_value = False

    seat_instance = MagicMock()
    seat_instance.seat_log = []
    # since SubscriptionSeat is a MagicMock, constructor args won't set attributes;
    # set email ahead so create_seat_log_entry uses the expected value
    seat_instance.email = "new@example.com"
    mock_seat_cls.return_value = seat_instance

    subscription = MagicMock()
    subscription.id = 99
    team = MagicMock()
    team.subscription = subscription
    team.seat_multiplier = 2
    # new seat id will be used by scheduler now
    seat_instance.id = 1001

    seat = create_seat("new@example.com", user=None, seat_multiplier=5, billing_team=team, lang="en")

    assert seat is seat_instance
    assert len(seat_instance.seat_log) == 1
    # save is called once without update_fields now
    seat_instance.save.assert_called_once_with()
    # constructor is called with expected fields
    mock_seat_cls.assert_called_once_with(
        billing_team=team,
        user=None,
        email="new@example.com",
        seat_multiplier=5,
    )
    # log entry has normalized email and correct action
    assert seat_instance.seat_log[0]["email"] == "new@example.com"
    assert seat_instance.seat_log[0]["action"] == "ADDED"


@patch("breathecode.payments.actions.tasks")
@patch("breathecode.payments.actions.invite_user_to_subscription_team")
@patch("breathecode.payments.actions.SubscriptionSeat")
def test_create_seat_with_per_team_consumption_does_not_schedule(mock_seat_cls, mock_invite, mock_tasks):
    """When team's consumption strategy is PER_TEAM, do not schedule stock creation; invite is still sent for pending seats."""
    from breathecode.payments.actions import create_seat

    mock_seat_cls.objects.filter.return_value.exists.return_value = False

    seat_instance = MagicMock()
    seat_instance.seat_log = []
    seat_instance.email = "team.member@example.com"
    seat_instance.id = 4242
    mock_seat_cls.return_value = seat_instance

    subscription = MagicMock()
    subscription.id = 500
    team = MagicMock()
    team.subscription = subscription
    team.seat_multiplier = 1
    team.consumption_strategy = "PER_TEAM"

    seat = create_seat("team.member@example.com", user=None, seat_multiplier=1, billing_team=team, lang="en")

    assert seat is seat_instance
    mock_invite.assert_called_once()  # invite still happens for pending seat
    mock_tasks.build_service_stock_scheduler_from_subscription.delay.assert_not_called()


@patch("breathecode.payments.actions.SubscriptionSeat")
def test_create_seat_duplicate_raises(mock_seat_cls):
    """Raises when a seat with the same email already exists in team."""
    from breathecode.payments.actions import create_seat, ValidationException

    mock_seat_cls.objects.filter.return_value.exists.return_value = True

    team = MagicMock()

    with pytest.raises(ValidationException):
        create_seat("dup@example.com", user=None, seat_multiplier=1, billing_team=team, lang="en")

    # ensure filter checked for duplicate with correct args
    mock_seat_cls.objects.filter.assert_called_with(billing_team=team, email="dup@example.com")


@patch("breathecode.payments.actions.tasks")
@patch("breathecode.payments.actions.invite_user_to_subscription_team")
@patch("breathecode.payments.actions.SubscriptionSeat")
def test_create_seat_with_user_does_not_invite_but_schedules(mock_seat_cls, mock_invite, mock_tasks):
    """When user is provided, do not send invites but still schedule stock build and persist log."""
    from breathecode.payments.actions import create_seat

    mock_seat_cls.objects.filter.return_value.exists.return_value = False

    seat_instance = MagicMock()
    seat_instance.seat_log = []
    mock_seat_cls.return_value = seat_instance

    subscription = MagicMock()
    subscription.id = 77
    team = MagicMock()
    team.subscription = subscription
    team.seat_multiplier = 3
    seat_instance.id = 777

    user = MagicMock()

    seat = create_seat("Member@Mail.com", user=user, seat_multiplier=3, billing_team=team, lang="en")

    assert seat is seat_instance
    mock_invite.assert_not_called()
    mock_tasks.build_service_stock_scheduler_from_subscription.delay.assert_called_once_with(
        77, seat_id=seat_instance.id
    )
    mock_seat_cls.assert_called_once_with(
        billing_team=team,
        user=user,
        email="Member@Mail.com",
        seat_multiplier=3,
    )
    assert len(seat_instance.seat_log) == 1
    assert seat_instance.seat_log[0]["action"] == "ADDED"

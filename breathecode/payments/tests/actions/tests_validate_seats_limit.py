import pytest
from unittest.mock import MagicMock, patch


@patch("breathecode.payments.actions.SubscriptionSeat")
def test_validate_seats_limit_within_limit(mock_seat_cls):
    """Does not raise when combined seat multipliers including adds/replaces are within limit."""
    from breathecode.payments.actions import validate_seats_limit

    a = MagicMock(email="a@mail.com", seat_multiplier=1)
    b = MagicMock(email="b@mail.com", seat_multiplier=2)
    mock_seat_cls.objects.filter.return_value = [a, b]

    team = MagicMock()
    team.seats_limit = 5

    add = [
        {"email": "c@mail.com", "seat_multiplier": 1, "first_name": "", "last_name": ""},
    ]
    replace = [
        {"from_email": "a@mail.com", "to_email": "d@mail.com", "first_name": "", "last_name": ""},
    ]

    validate_seats_limit(team, add, replace, lang="en")


@patch("breathecode.payments.actions.SubscriptionSeat")
def test_validate_seats_limit_exceeds_raises(mock_seat_cls):
    """Raises ValidationException when computed seats exceed team.seats_limit."""
    from breathecode.payments.actions import validate_seats_limit, ValidationException

    a = MagicMock(email="a@mail.com", seat_multiplier=2)
    mock_seat_cls.objects.filter.return_value = [a]

    team = MagicMock()
    team.seats_limit = 2

    add = [
        {"email": "b@mail.com", "seat_multiplier": 2, "first_name": "", "last_name": ""},
    ]
    replace = []

    with pytest.raises(ValidationException, match="seats-limit-exceeded"):
        validate_seats_limit(team, add, replace, lang="en")

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from pytz import UTC


@patch("breathecode.payments.actions.timezone")
def test_create_seat_log_entry_normalizes_email_and_formats_timestamp(mock_timezone):
    """create_seat_log_entry should lowercase/strip email and format created_at with Z suffix."""
    from breathecode.payments.actions import create_seat_log_entry

    fixed_dt = datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)
    mock_timezone.now.return_value = fixed_dt

    seat = MagicMock()
    seat.email = "  USER@Example.Com  "

    entry = create_seat_log_entry(seat, "ADDED")

    assert entry["email"] == "user@example.com"
    assert entry["action"] == "ADDED"
    assert entry["created_at"] == fixed_dt.isoformat().replace("+00:00", "Z")

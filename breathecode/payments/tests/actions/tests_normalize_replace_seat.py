def test_normalize_replace_seat_defaults_and_normalizes_emails():
    """normalize_replace_seat applies defaults and normalizes both from/to emails."""
    from breathecode.payments.actions import normalize_replace_seat

    seats = [
        {"from_email": " OLD@MAIL.com ", "to_email": " NEW@MAIL.com ", "first_name": "N", "last_name": "L"},
        {"from_email": " a@b.com ", "to_email": " c@d.com "},
    ]
    res = normalize_replace_seat(seats)

    assert res[0]["from_email"] == "old@mail.com"
    assert res[0]["to_email"] == "new@mail.com"
    assert res[0]["first_name"] == "N"
    assert res[0]["last_name"] == "L"

    assert res[1]["from_email"] == "a@b.com"
    assert res[1]["to_email"] == "c@d.com"
    assert res[1]["first_name"] == ""
    assert res[1]["last_name"] == ""

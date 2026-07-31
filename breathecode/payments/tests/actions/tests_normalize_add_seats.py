def test_normalize_add_seats_defaults_and_normalizes_email():
    """normalize_add_seats applies defaults and normalizes email."""
    from breathecode.payments.actions import normalize_add_seats

    seats = [
        {"email": " A@B.COM ", "first_name": "A", "last_name": "B", "cohort_id": 42},
        {"email": " X@Y.COM "},
    ]
    res = normalize_add_seats(seats)

    assert res[0]["email"] == "a@b.com"
    assert res[0]["first_name"] == "A"
    assert res[0]["last_name"] == "B"
    assert res[0]["cohort_id"] == 42

    assert res[1]["email"] == "x@y.com"
    assert res[1]["first_name"] == ""
    assert res[1]["last_name"] == ""
    assert res[1]["cohort_id"] is None

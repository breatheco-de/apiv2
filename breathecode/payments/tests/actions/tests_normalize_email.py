def test_normalize_email_trims_and_lowercases():
    """normalize_email should strip and lowercase the input."""
    from breathecode.payments.actions import normalize_email

    assert normalize_email("  User@Example.COM  ") == "user@example.com"

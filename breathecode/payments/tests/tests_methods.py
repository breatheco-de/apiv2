import capyc.pytest as capy  # Import capy
import pytest  # Import pytest
from django.urls import reverse_lazy


# Using pytest style functions instead of class methods
@pytest.mark.django_db  # Enable DB access
def test_methods__no_payment_methods(client, database: capy.Database):  # Use capy.Database
    """
    Test /methods endpoint when no PaymentMethod objects exist.
    Expected: 200 OK with an empty list.
    """
    # Arrange
    # No user authentication needed now
    url = reverse_lazy("payments:methods")

    # Act
    response = client.get(url)
    json_response = response.json()

    # Assert
    assert json_response == []
    assert response.status_code == 200
    assert database.list_of("payments.PaymentMethod") == []


@pytest.mark.django_db  # Enable DB access
def test_methods__with_data(client, database: capy.Database):
    """
    Test /methods endpoint with existing PaymentMethod objects.
    Expected: 200 OK with serialized data of all payment methods.
    """
    # Arrange
    # No user authentication needed now
    model = database.create(
        city=1,
        country=1,
        currency=1,
        academy=1,
        payment_method=(
            2,
            {
                "academy_id": 1,
                "currency_id": 1,
                "title": "Method Title",  # Use static title
                "lang": "en-US",
            },
        ),
    )
    url = reverse_lazy("payments:methods")

    # Act
    response = client.get(url)
    json_response = response.json()

    # Assert
    assert len(json_response) == 2
    assert response.status_code == 200
    assert {pm["id"] for pm in json_response} == {pm.id for pm in model.payment_method}
    assert len(database.list_of("payments.PaymentMethod")) == 2


# --- Grouped Country Code Filter Tests ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    "included_codes_list, filter_code, expected_count, expected_ids_indices",
    [
        # Case 1: Empty string and specific match, filter US -> Both included
        # '' means available everywhere, 'US,CA' contains US
        (
            ["", "US,CA"],
            "US",
            2,
            [0, 1],
        ),
        # Case 2: Specific match and no match, filter US -> Only matching included
        (
            ["GB,DE", "US,CA"],
            "US",
            1,
            [1],  # Only the second item matches
        ),
        # Case 3: No match, filter US -> None included
        (
            ["GB,DE", "CA,MX"],
            "US",
            0,
            [],
        ),
        # Case 4: Mix (Match, Empty, No Match), filter US -> First two included
        (
            ["US,CA", "", "GB,DE"],
            "US",
            2,
            [0, 1],  # First matches 'US', Second is empty string
        ),
        # Case 5: No filter code provided -> All included
        (
            ["US,CA", "", "GB,DE"],
            None,  # No country_code filter
            3,
            [0, 1, 2],
        ),
        # Case 6: Case insensitive match
        (
            ["us,ca", "gb,de"],  # Stored codes are lowercase
            "US",  # Filter code is uppercase
            1,
            [0],  # Should match the first item due to icontains
        ),
    ],
)
def test_methods__filter_by_country_code(
    client, database: capy.Database, included_codes_list, filter_code, expected_count, expected_ids_indices
):
    """
    Test filtering by country_code with various scenarios.
    """
    # Arrange
    # No user authentication needed now
    payment_methods_data = [
        {"included_country_codes": codes, "title": f"Method {i}"} for i, codes in enumerate(included_codes_list)
    ]
    model = database.create(city=1, country=1, academy=1, currency=1, payment_method=payment_methods_data)

    url = reverse_lazy("payments:methods")
    if filter_code:
        url += f"?country_code={filter_code}"

    # Act
    response = client.get(url)
    json_response = response.json()
    returned_ids = {item["id"] for item in json_response}

    # Assert
    assert len(json_response) == expected_count
    expected_ids = {model.payment_method[i].id for i in expected_ids_indices}
    assert returned_ids == expected_ids
    assert response.status_code == 200


# --- Grouped Other Filter Tests ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    "filter_key, filter_value, setup_data, expected_count, expected_index",
    [
        # Filter by lang
        (
            "lang",
            "es-ES",
            [{"lang": "en-US", "title": "EN"}, {"lang": "es-ES", "title": "ES"}],
            1,
            1,  # Expecting the second item (index 1)
        ),
        # Filter by lang - no results
        ("lang", "fr-FR", [{"lang": "en-US", "title": "EN"}, {"lang": "es-ES", "title": "ES"}], 0, None),
        # Filter by academy_id
        (
            "academy__id",
            1,  # Filter for academy 1
            [{"academy_id": 1, "title": "A1"}, {"academy_id": 2, "title": "A2"}],
            1,
            0,  # Expecting the first item (index 0)
        ),
        # Filter by academy_id - no results
        (
            "academy__id",
            3,  # Filter for non-existent academy 3
            [{"academy_id": 1, "title": "A1"}, {"academy_id": 2, "title": "A2"}],
            0,
            None,
        ),
        # Filter by currency_code
        (
            "currency__code",
            "USD",
            [{"currency_id": 1, "title": "USD"}, {"currency_id": 2, "title": "EUR"}],
            1,
            0,  # Expecting the first item (index 0)
        ),
        # Filter by currency_code - no results
        ("currency__code", "GBP", [{"currency_id": 1, "title": "USD"}, {"currency_id": 2, "title": "EUR"}], 0, None),
    ],
)
def test_methods__filters_exact(
    client, database: capy.Database, filter_key, filter_value, setup_data, expected_count, expected_index
):
    """
    Test filtering by exact matches for lang, academy__id, and currency__code.
    """
    # Arrange
    # No user authentication needed now

    # Ensure related models exist or are created by database.create
    model = database.create(
        city=1,
        country=1,
        academy=len({d.get("academy_id") for d in setup_data if d.get("academy_id")}),
        currency=[
            {"code": "USD", "name": "US Dollar"},
            {"code": "EUR", "name": "Euro"},
            {"code": "GBP", "name": "Pound Sterling"},  # Add GBP if needed by tests
        ],
    )
    currencies = model.currency
    academies = model.academy if "academy" in model else []

    # Map IDs for creation if not provided directly
    currency_map = {c.code: c.id for c in currencies}
    academy_map = {a.id: a.id for a in academies}  # Simple map assuming IDs match creation order index + 1

    payment_methods_data = []
    for data in setup_data:
        if "currency_id" in data and data["currency_id"] == 1:  # Map test currency IDs
            data["currency_id"] = currency_map["USD"]
        elif "currency_id" in data and data["currency_id"] == 2:
            data["currency_id"] = currency_map["EUR"]

        if "academy_id" in data and data["academy_id"] in academy_map:
            data["academy_id"] = academy_map[data["academy_id"]]
        elif "academy_id" not in data:  # Assign default academy if needed
            data["academy_id"] = (
                academies[0].id if academies else database.create(city=1, country=1, academy=1).academy.id
            )

        # Ensure default currency if not specified
        if "currency_id" not in data:
            data["currency_id"] = currency_map["USD"]

        payment_methods_data.append(data)

    model = database.create(city=1, country=1, payment_method=payment_methods_data)

    url = reverse_lazy("payments:methods") + f"?{filter_key}={filter_value}"

    # Act
    response = client.get(url)
    json_response = response.json()

    # Assert
    assert len(json_response) == expected_count
    if expected_count > 0 and expected_index is not None:
        assert json_response[0]["id"] == model.payment_method[expected_index].id
    assert response.status_code == 200

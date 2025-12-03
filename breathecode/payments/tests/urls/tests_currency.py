"""
Tests for /v1/payments/currency endpoint
"""

import capyc.pytest as capy
import pytest
from django.urls import reverse_lazy
from rest_framework import status


@pytest.fixture(autouse=True)
def setup(db):
    yield


def test_currency_no_data(client: capy.Client):
    """Test GET /currency with no currencies in database"""
    url = reverse_lazy("payments:currency")
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert json == []


def test_currency_list(database: capy.Database, client: capy.Client):
    """Test GET /currency returns all currencies"""
    model = database.create(currency=(3, {"code": "USD"}, {"code": "EUR"}, {"code": "MXN"}))

    url = reverse_lazy("payments:currency")
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json) == 3
    
    # Check that currencies are sorted by code (default sort)
    codes = [c["code"] for c in json]
    assert codes == ["EUR", "MXN", "USD"]
    
    # Verify structure
    for currency in json:
        assert "code" in currency
        assert "name" in currency
        assert "countries" in currency


def test_currency_filter_by_code(database: capy.Database, client: capy.Client):
    """Test GET /currency?code=USD filters by currency code"""
    model = database.create(currency=(3, {"code": "USD"}, {"code": "EUR"}, {"code": "MXN"}))

    url = reverse_lazy("payments:currency")
    response = client.get(url, {"code": "USD"})

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json) == 1
    assert json[0]["code"] == "USD"


def test_currency_filter_by_name(database: capy.Database, client: capy.Client):
    """Test GET /currency?name=Dollar filters by currency name"""
    model = database.create(
        currency=(
            3,
            {"code": "USD", "name": "US Dollar"},
            {"code": "EUR", "name": "Euro"},
            {"code": "CAD", "name": "Canadian Dollar"},
        )
    )

    url = reverse_lazy("payments:currency")
    response = client.get(url, {"name": "Dollar"})

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json) == 2
    codes = {c["code"] for c in json}
    assert codes == {"USD", "CAD"}


def test_currency_by_code(database: capy.Database, client: capy.Client):
    """Test GET /currency/{currency_code} returns specific currency"""
    model = database.create(currency={"code": "USD", "name": "US Dollar"})

    url = reverse_lazy("payments:currency_code", kwargs={"currency_code": "USD"})
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert json["code"] == "USD"
    assert json["name"] == "US Dollar"
    assert "countries" in json


def test_currency_by_code_lowercase(database: capy.Database, client: capy.Client):
    """Test GET /currency/{currency_code} with lowercase code"""
    model = database.create(currency={"code": "USD", "name": "US Dollar"})

    url = reverse_lazy("payments:currency_code", kwargs={"currency_code": "usd"})
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert json["code"] == "USD"


def test_currency_by_code_not_found(client: capy.Client):
    """Test GET /currency/{currency_code} with non-existent code"""
    url = reverse_lazy("payments:currency_code", kwargs={"currency_code": "XXX"})
    response = client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    json = response.json()
    assert json["slug"] == "currency-not-found"


def test_currency_with_countries(database: capy.Database, client: capy.Client):
    """Test currency response includes associated countries"""
    model = database.create(
        country=(2, {"code": "US", "name": "United States"}, {"code": "EC", "name": "Ecuador"}),
        currency={"code": "USD", "name": "US Dollar"},
    )
    
    # Associate countries with currency
    model.currency.countries.set(model.country)

    url = reverse_lazy("payments:currency_code", kwargs={"currency_code": "USD"})
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["countries"]) == 2
    country_codes = {c["code"] for c in json["countries"]}
    assert country_codes == {"US", "EC"}


def test_currency_pagination(database: capy.Database, client: capy.Client):
    """Test currency list supports pagination"""
    # Create 15 currencies
    currencies = []
    for i in range(15):
        currencies.append({"code": f"C{i:02d}", "name": f"Currency {i}"})
    
    model = database.create(currency=tuple(currencies))

    url = reverse_lazy("payments:currency")
    response = client.get(url, {"limit": 10, "offset": 0})

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert "count" in json
    assert json["count"] == 15
    assert len(json["results"]) == 10


def test_currency_sorting(database: capy.Database, client: capy.Client):
    """Test currency list can be sorted"""
    model = database.create(
        currency=(
            3,
            {"code": "MXN", "name": "Mexican Peso"},
            {"code": "USD", "name": "US Dollar"},
            {"code": "EUR", "name": "Euro"},
        )
    )

    # Sort by name descending
    url = reverse_lazy("payments:currency")
    response = client.get(url, {"sort": "-name"})

    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    names = [c["name"] for c in json]
    assert names == ["US Dollar", "Mexican Peso", "Euro"]


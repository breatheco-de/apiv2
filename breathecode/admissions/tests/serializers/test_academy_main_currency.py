"""
Tests for Academy serializers with main_currency field
"""

import capyc.pytest as capy
import pytest
from capyc.rest_framework.exceptions import ValidationException

from breathecode.admissions.serializers import AcademyPOSTSerializer, AcademySerializer


@pytest.fixture(autouse=True)
def setup(db):
    yield


def test_academy_serializer_main_currency_with_code(database: capy.Database):
    """Test updating academy with currency code"""
    model = database.create(academy=1, currency={"code": "USD", "name": "US Dollar"})

    data = {"main_currency": "USD"}
    serializer = AcademySerializer(model.academy, data=data, partial=True)

    assert serializer.is_valid()
    academy = serializer.save()

    assert academy.main_currency.id == model.currency.id
    assert academy.main_currency.code == "USD"


def test_academy_serializer_main_currency_with_lowercase_code(database: capy.Database):
    """Test updating academy with lowercase currency code"""
    model = database.create(academy=1, currency={"code": "EUR", "name": "Euro"})

    data = {"main_currency": "eur"}
    serializer = AcademySerializer(model.academy, data=data, partial=True)

    assert serializer.is_valid()
    academy = serializer.save()

    assert academy.main_currency.id == model.currency.id
    assert academy.main_currency.code == "EUR"


def test_academy_serializer_main_currency_with_id(database: capy.Database):
    """Test updating academy with currency ID"""
    model = database.create(academy=1, currency={"code": "MXN", "name": "Mexican Peso"})

    data = {"main_currency": model.currency.id}
    serializer = AcademySerializer(model.academy, data=data, partial=True)

    assert serializer.is_valid()
    academy = serializer.save()

    assert academy.main_currency.id == model.currency.id
    assert academy.main_currency.code == "MXN"


def test_academy_serializer_main_currency_invalid_code(database: capy.Database):
    """Test updating academy with invalid currency code"""
    model = database.create(academy=1)

    data = {"main_currency": "XXX"}
    serializer = AcademySerializer(model.academy, data=data, partial=True)

    with pytest.raises(ValidationException, match="currency-not-found"):
        serializer.is_valid(raise_exception=True)


def test_academy_serializer_main_currency_invalid_id(database: capy.Database):
    """Test updating academy with invalid currency ID"""
    model = database.create(academy=1)

    data = {"main_currency": 9999}
    serializer = AcademySerializer(model.academy, data=data, partial=True)

    with pytest.raises(ValidationException, match="currency-not-found"):
        serializer.is_valid(raise_exception=True)


def test_academy_serializer_main_currency_null(database: capy.Database):
    """Test updating academy with null currency"""
    model = database.create(academy=1, currency={"code": "USD"})
    model.academy.main_currency = model.currency
    model.academy.save()

    data = {"main_currency": None}
    serializer = AcademySerializer(model.academy, data=data, partial=True)

    assert serializer.is_valid()
    academy = serializer.save()

    assert academy.main_currency is None


def test_academy_post_serializer_main_currency_with_code(database: capy.Database):
    """Test creating academy with currency code"""
    model = database.create(city=1, country=1, currency={"code": "USD", "name": "US Dollar"})

    data = {
        "slug": "new-academy",
        "name": "New Academy",
        "logo_url": "https://example.com/logo.png",
        "street_address": "123 Main St",
        "city": model.city.id,
        "country": model.country.id,
        "main_currency": "USD",
    }
    serializer = AcademyPOSTSerializer(data=data)

    assert serializer.is_valid()
    academy = serializer.save()

    assert academy.main_currency.id == model.currency.id
    assert academy.main_currency.code == "USD"


def test_academy_post_serializer_main_currency_with_id(database: capy.Database):
    """Test creating academy with currency ID"""
    model = database.create(city=1, country=1, currency={"code": "EUR", "name": "Euro"})

    data = {
        "slug": "another-academy",
        "name": "Another Academy",
        "logo_url": "https://example.com/logo.png",
        "street_address": "456 Another St",
        "city": model.city.id,
        "country": model.country.id,
        "main_currency": model.currency.id,
    }
    serializer = AcademyPOSTSerializer(data=data)

    assert serializer.is_valid()
    academy = serializer.save()

    assert academy.main_currency.id == model.currency.id
    assert academy.main_currency.code == "EUR"


def test_academy_post_serializer_without_main_currency(database: capy.Database):
    """Test creating academy without main_currency"""
    model = database.create(city=1, country=1)

    data = {
        "slug": "no-currency-academy",
        "name": "No Currency Academy",
        "logo_url": "https://example.com/logo.png",
        "street_address": "789 Third St",
        "city": model.city.id,
        "country": model.country.id,
    }
    serializer = AcademyPOSTSerializer(data=data)

    assert serializer.is_valid()
    academy = serializer.save()

    assert academy.main_currency is None


def test_academy_post_serializer_main_currency_invalid_code(database: capy.Database):
    """Test creating academy with invalid currency code"""
    model = database.create(city=1, country=1)

    data = {
        "slug": "invalid-currency-academy",
        "name": "Invalid Currency Academy",
        "logo_url": "https://example.com/logo.png",
        "street_address": "321 Fourth St",
        "city": model.city.id,
        "country": model.country.id,
        "main_currency": "XXX",
    }
    serializer = AcademyPOSTSerializer(data=data)

    with pytest.raises(ValidationException, match="currency-not-found"):
        serializer.is_valid(raise_exception=True)


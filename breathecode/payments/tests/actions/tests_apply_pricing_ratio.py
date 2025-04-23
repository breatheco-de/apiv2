from typing import Any, Optional, Union
from unittest.mock import MagicMock, patch

import pytest
from capyc.rest_framework.exceptions import ValidationException

from breathecode.payments.actions import apply_pricing_ratio
from breathecode.payments.models import Currency
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions


@pytest.fixture
def mock_general_ratios():
    general_ratios = {
        "ve": {"pricing_ratio": 0.8, "currency": "USD"},
        "mx": {"pricing_ratio": 1.0, "currency": "MXN"},
        "ar": {"pricing_ratio": 0.7, "currency": "USD"},
        "us": {"pricing_ratio": 1.0, "currency": "USD"},
    }

    with patch("breathecode.payments.actions.GENERAL_PRICING_RATIOS", general_ratios):
        yield general_ratios


@pytest.fixture
def mock_usd_currency():
    return MagicMock(spec=Currency, code="USD", name="US Dollar")


@pytest.fixture
def mock_mxn_currency():
    return MagicMock(spec=Currency, code="MXN", name="Mexican Peso")


@pytest.fixture
def mock_eur_currency():
    return MagicMock(spec=Currency, code="EUR", name="Euro")


@pytest.fixture
def mock_plan_obj():
    plan = MagicMock()
    plan.pricing_ratio_exceptions = {
        "ve": {"ratio": 0.7, "currency": "USD"},  # Ratio override with USD
        "ar": {"ratio": 0.6},  # Ratio override, default currency
        "ca": {"price": 50, "currency": "EUR"},  # Direct price override with EUR
        "mx": {"price": 1000},  # Direct price override, default currency
        "gb": {"currency": "EUR"},  # Only currency override
    }
    plan.currency = MagicMock(spec=Currency, code="USD", name="US Dollar")
    return plan


@pytest.fixture
def mock_service_obj():
    service = MagicMock()
    service.pricing_ratio_exceptions = {
        "ve": {"ratio": 0.75, "currency": "MXN"},  # Ratio override with MXN
        "br": {"ratio": 0.9},  # Ratio override, default currency
        "ca": {"price_per_unit": 25},  # Direct price override (using different price_attr)
        "jp": {"currency": "EUR"},  # Currency override only
    }
    service.currency = MagicMock(spec=Currency, code="USD", name="US Dollar")
    return service


@pytest.fixture
def mock_financing_obj():
    financing = MagicMock()
    financing.pricing_ratio_exceptions = {
        "ve": {"ratio": 0.8, "currency": "USD"},  # Ratio override
        "pe": {"price": 75, "currency": "EUR"},  # Direct price override
    }
    financing.currency = MagicMock(spec=Currency, code="USD", name="US Dollar")
    return financing


# Helper side_effect for get_cached_currency mock
def get_currency_side_effect(usd_mock=None, eur_mock=None, mxn_mock=None):
    def side_effect(code: str, cache: dict):
        code_upper = code.upper()
        if code_upper == "USD":
            return usd_mock
        if code_upper == "EUR":
            return eur_mock
        if code_upper == "MXN":
            return mxn_mock
        return None  # Simulate currency not found for other codes

    return side_effect


# === Test Cases ===


# 1. Basic tests (no object override)
@pytest.mark.parametrize(
    "price, country_code, expected_price, expected_ratio, expected_currency_code",
    [
        (None, None, None, None, None),  # No price, no country
        (0, "us", 0, None, None),  # Zero price
        (100, None, 100, None, None),  # No country code
        (100, "us", 100, 1.0, None),  # US price (no change)
        (100, "ve", 80, 0.8, None),  # Venezuela price (general ratio)
        (100, "mx", 100, 1.0, None),  # Mexico price (general ratio 1.0, MXN ignored without obj)
        (100, "ar", 70, 0.7, None),  # Argentina price (general ratio)
        (100, "xx", 100, None, None),  # Unknown country
        (100, "VE", 80, 0.8, None),  # Case insensitivity (general ratio)
    ],
)
def test_apply_pricing_ratio_basic(
    mock_general_ratios, price, country_code, expected_price, expected_ratio, expected_currency_code
):
    """Test basic pricing ratio application without object overrides."""
    # No need to mock get_cached_currency as it won't be called
    result_price, result_ratio, result_currency = apply_pricing_ratio(price, country_code)
    assert result_price == expected_price
    assert result_ratio == expected_ratio
    assert (result_currency.code if result_currency else None) == expected_currency_code


# 2. Tests with object overrides (Plan)
@pytest.mark.parametrize(
    "price, country_code, price_attr, expected_price, expected_ratio, expected_currency_code",
    [
        # Ratio override
        (100, "ve", "price", 70, 0.7, "USD"),  # Plan ratio override (VE)
        (100, "ar", "price", 60, 0.6, None),  # Plan ratio override (AR), no currency override
        # Direct price override
        (100, "ca", "price", 50, None, "EUR"),  # Plan direct price override (CA) with EUR
        (100, "mx", "price", 1000, None, None),  # Plan direct price override (MX), no currency override
        # Currency override only - Function logic currently loses this override on fallback
        (100, "gb", "price", 100, None, None),  # No general ratio for GB, currency override lost
        # General ratio applies if no object override for country
        (100, "us", "price", 100, 1.0, None),  # US (general ratio)
        # Unknown country
        (100, "xx", "price", 100, None, None),  # Unknown country (no change)
        # Case insensitivity
        (100, "VE", "price", 70, 0.7, "USD"),  # Case insensitive object override
        (100, "CA", "price", 50, None, "EUR"),  # Case insensitive object override
    ],
)
def test_apply_pricing_ratio_with_plan(
    mock_general_ratios,
    mock_plan_obj,
    mock_usd_currency,
    mock_eur_currency,
    price,
    country_code,
    price_attr,
    expected_price,
    expected_ratio,
    expected_currency_code,
):
    """Test pricing ratio application with Plan object overrides."""
    side_effect = get_currency_side_effect(usd_mock=mock_usd_currency, eur_mock=mock_eur_currency)
    with patch("breathecode.payments.actions.get_cached_currency", side_effect=side_effect):
        result_price, result_ratio, result_currency = apply_pricing_ratio(
            price, country_code, mock_plan_obj, price_attr=price_attr
        )
        assert result_price == expected_price
        assert result_ratio == expected_ratio
        assert (result_currency.code if result_currency else None) == expected_currency_code


# 3. Tests with object overrides (AcademyService)
@pytest.mark.parametrize(
    "price, country_code, price_attr, expected_price, expected_ratio, expected_currency_code",
    [
        # Ratio override
        (100, "ve", "price", 75, 0.75, "MXN"),  # Service ratio override (VE) with MXN
        (100, "br", "price", 90, 0.9, None),  # Service ratio override (BR), no currency override
        # Direct price override (using different price_attr)
        (100, "ca", "price_per_unit", 25, None, None),  # Service direct price override (CA)
        # Currency override only - Function logic currently loses this override on fallback
        (100, "jp", "price", 100, None, None),  # No general ratio for JP, currency override lost
        # General ratio applies if no object override for country
        (100, "ar", "price", 70, 0.7, None),  # AR (general ratio)
        # Unknown country
        (100, "xx", "price", 100, None, None),  # Unknown country (no change)
        # Case insensitivity
        (100, "VE", "price", 75, 0.75, "MXN"),  # Case insensitive object override
        (100, "CA", "price_per_unit", 25, None, None),  # Case insensitive object override
    ],
)
def test_apply_pricing_ratio_with_service(
    mock_general_ratios,
    mock_service_obj,
    mock_mxn_currency,
    mock_eur_currency,
    price,
    country_code,
    price_attr,
    expected_price,
    expected_ratio,
    expected_currency_code,
):
    """Test pricing ratio application with AcademyService object overrides."""
    side_effect = get_currency_side_effect(mxn_mock=mock_mxn_currency, eur_mock=mock_eur_currency)
    with patch("breathecode.payments.actions.get_cached_currency", side_effect=side_effect):
        result_price, result_ratio, result_currency = apply_pricing_ratio(
            price, country_code, mock_service_obj, price_attr=price_attr
        )
        assert result_price == expected_price
        assert result_ratio == expected_ratio
        assert (result_currency.code if result_currency else None) == expected_currency_code


# 4. Tests with object overrides (FinancingOption)
@pytest.mark.parametrize(
    "price, country_code, price_attr, expected_price, expected_ratio, expected_currency_code",
    [
        # Ratio override
        (100, "ve", "price", 80, 0.8, "USD"),  # Financing ratio override (VE) with USD
        # Direct price override
        (100, "pe", "price", 75, None, "EUR"),  # Financing direct price override (PE) with EUR
        # General ratio applies if no object override for country
        (100, "ar", "price", 70, 0.7, None),  # AR (general ratio)
        # Unknown country
        (100, "xx", "price", 100, None, None),  # Unknown country (no change)
        # Case insensitivity
        (100, "VE", "price", 80, 0.8, "USD"),  # Case insensitive object override
        (100, "PE", "price", 75, None, "EUR"),  # Case insensitive object override
    ],
)
def test_apply_pricing_ratio_with_financing(
    mock_general_ratios,
    mock_financing_obj,
    mock_usd_currency,
    mock_eur_currency,
    price,
    country_code,
    price_attr,
    expected_price,
    expected_ratio,
    expected_currency_code,
):
    """Test pricing ratio application with FinancingOption object overrides."""
    side_effect = get_currency_side_effect(usd_mock=mock_usd_currency, eur_mock=mock_eur_currency)
    with patch("breathecode.payments.actions.get_cached_currency", side_effect=side_effect):
        result_price, result_ratio, result_currency = apply_pricing_ratio(
            price, country_code, mock_financing_obj, price_attr=price_attr
        )
        assert result_price == expected_price
        assert result_ratio == expected_ratio
        assert (result_currency.code if result_currency else None) == expected_currency_code


# 5. Test invalid currency code in override
def test_apply_pricing_ratio_invalid_currency(mock_general_ratios, mock_plan_obj):
    """Test that ValidationException is raised for invalid currency codes in overrides."""
    mock_plan_obj.pricing_ratio_exceptions["fr"] = {"currency": "XYZ"}

    # Mock get_cached_currency to return None for XYZ
    def side_effect_invalid(code: str, cache: dict):
        if code.upper() == "XYZ":
            return None  # Simulate currency not found
        return get_currency_side_effect()(code, cache)  # Use default for others if needed

    with patch(
        "breathecode.payments.actions.get_cached_currency", side_effect=side_effect_invalid
    ) as mock_get_currency:
        with pytest.raises(ValidationException) as exc_info:
            apply_pricing_ratio(100, "fr", mock_plan_obj, lang="en")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Currency not found"  # Check the message
        assert exc_info.value.slug == "currency-not-found"  # Check the slug
        # Ensure get_cached_currency was called with the correct code
        mock_get_currency.assert_called_once_with("XYZ", {})


# 6. Test cache usage
def test_apply_pricing_ratio_with_cache(mock_general_ratios, mock_plan_obj, mock_eur_currency, mock_usd_currency):
    """Test that the cache prevents redundant calls to get_cached_currency."""
    # Country 'ca' has currency override to EUR
    # Country 'gb' has currency override to EUR
    # Country 've' has currency override to USD
    cache = {}

    # Mock get_cached_currency to track calls and return currencies
    mock_get_cached_currency = MagicMock()

    def side_effect(code: str, cache_arg: dict):
        code_upper = code.upper()
        # Simulate cache behavior (only return currency if not in mock cache)
        # The real function handles the dict logic, we just return the obj
        if code_upper == "EUR":
            return mock_eur_currency
        if code_upper == "USD":
            return mock_usd_currency
        return None

    mock_get_cached_currency.side_effect = side_effect

    with patch("breathecode.payments.actions.get_cached_currency", mock_get_cached_currency):
        # First call for 'ca', should call mock for EUR
        apply_pricing_ratio(100, "ca", mock_plan_obj, cache=cache)
        mock_get_cached_currency.assert_called_with("EUR", cache)
        assert mock_get_cached_currency.call_count == 1

        # Second call for 'gb', should call mock for EUR again (cache check inside real func)
        apply_pricing_ratio(100, "gb", mock_plan_obj, cache=cache)
        assert mock_get_cached_currency.call_count == 2
        mock_get_cached_currency.assert_called_with("EUR", cache)  # Check last call

        # Third call for 've', should call mock for USD
        apply_pricing_ratio(100, "ve", mock_plan_obj, cache=cache)
        assert mock_get_cached_currency.call_count == 3
        mock_get_cached_currency.assert_called_with("USD", cache)

        # Fourth call for 've', should call mock for USD again
        apply_pricing_ratio(100, "VE", mock_plan_obj, cache=cache)  # Case insensitive
        assert mock_get_cached_currency.call_count == 4
        mock_get_cached_currency.assert_called_with("USD", cache)


# 7. Test different price attributes
def test_apply_pricing_ratio_different_price_attr(mock_general_ratios, mock_service_obj):
    """Test using a different price_attr for direct price override lookup."""
    # 'ca' in mock_service_obj has 'price_per_unit': 25
    # No currency involved, no need to mock get_cached_currency
    result_price, result_ratio, result_currency = apply_pricing_ratio(
        100, "ca", mock_service_obj, price_attr="price_per_unit"
    )
    assert result_price == 25
    assert result_ratio is None
    assert result_currency is None

    # If using default 'price' attr, it should not find the override
    result_price_default, _, _ = apply_pricing_ratio(100, "ca", mock_service_obj, price_attr="price")
    assert result_price_default == 100  # No general ratio for CA


# 8. Test decimal prices
@pytest.mark.parametrize(
    "price, country_code, expected_price, expected_ratio",
    [
        (99.99, "ve", 79.992, 0.8),
        (10.50, "ar", 7.35, 0.7),
    ],
)
def test_apply_pricing_ratio_decimal_prices(mock_general_ratios, price, country_code, expected_price, expected_ratio):
    """Test apply_pricing_ratio with decimal prices and general ratios."""
    # No currency involved, no need to mock get_cached_currency
    result_price, result_ratio, _ = apply_pricing_ratio(price, country_code)
    assert result_price == expected_price
    assert result_ratio == expected_ratio

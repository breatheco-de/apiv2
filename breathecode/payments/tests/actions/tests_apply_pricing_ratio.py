from typing import Any, Optional, Union
from unittest.mock import MagicMock, patch

import pytest

from breathecode.payments.actions import apply_pricing_ratio


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
def plan_with_ratio_exceptions():
    plan = MagicMock()
    plan.pricing_ratio_exceptions = {
        "ve": {"ratio": 0.7},  # Override general ratio for Venezuela
        "ar": {"ratio": 0.6},  # Override general ratio for Argentina
        "ca": {"price": 50},  # Direct price override for Canada
    }
    return plan


@pytest.fixture
def academy_service_with_ratio_exceptions():
    academy_service = MagicMock()
    academy_service.pricing_ratio_exceptions = {
        "ve": {"ratio": 0.75},  # Override general ratio for Venezuela
        "br": {"ratio": 0.9},  # Override general ratio for Brazil
        "ca": {"price": 25},  # Direct price override for Canada
    }
    return academy_service


@pytest.mark.parametrize(
    "price,country_code,expected_price,expected_ratio",
    [
        (None, None, None, None),  # No price, no country
        (0, "us", 0, None),  # Zero price
        (100, None, 100, None),  # No country code
        (100, "us", 100, 1.0),  # US price (no change)
        (100, "ve", 80, 0.8),  # Venezuela price
        (100, "ar", 70, 0.7),  # Argentina price
        (100, "xx", 100, None),  # Unknown country
    ],
)
def test_apply_pricing_ratio_basic(mock_general_ratios, price, country_code, expected_price, expected_ratio):
    """Test basic pricing ratio application without object overrides"""
    result_price, result_ratio = apply_pricing_ratio(price, country_code)
    assert result_price == expected_price
    assert result_ratio == expected_ratio


def test_apply_pricing_ratio_with_direct_price_override():
    """Test that direct price overrides in object exceptions take precedence"""
    plan = MagicMock()
    plan.pricing_ratio_exceptions = {
        "ve": {"price": 50},  # Direct price override
    }

    result_price, result_ratio = apply_pricing_ratio(100, "ve", plan)
    assert result_price == 50
    assert result_ratio is None  # Ratio should be None for direct price override


def test_apply_pricing_ratio_with_ratio_override():
    """Test that ratio overrides in object exceptions work"""
    plan = MagicMock()
    plan.pricing_ratio_exceptions = {
        "ve": {"ratio": 0.5},  # Custom ratio override
    }

    result_price, result_ratio = apply_pricing_ratio(100, "ve", plan)
    assert result_price == 50
    assert result_ratio == 0.5


def test_apply_pricing_ratio_case_insensitive():
    """Test that country codes are case insensitive"""
    plan = MagicMock()
    plan.pricing_ratio_exceptions = {
        "ve": {"ratio": 0.5},
    }

    result_price, result_ratio = apply_pricing_ratio(100, "VE", plan)
    assert result_price == 50
    assert result_ratio == 0.5


@pytest.mark.parametrize(
    "price,country_code,x_type,expected_price,expected_ratio",
    [
        (100.0, "ve", "plan", 70.0, 0.7),  # Plan override
        (100.0, "ca", "plan", 50.0, None),  # Plan direct price
        (100.0, "ve", "service", 75.0, 0.75),  # Service override
        (100.0, "ca", "service", 25.0, None),  # Service direct price
        (100.0, "jp", "plan", 100.0, None),  # Unsupported country
    ],
)
def test_apply_pricing_ratio_with_exceptions(
    price: float,
    country_code: str,
    x_type: str,
    expected_price: float,
    expected_ratio: Optional[float],
    plan_with_ratio_exceptions: MagicMock,
    academy_service_with_ratio_exceptions: MagicMock,
    mock_general_ratios: dict,
) -> None:
    """Test apply_pricing_ratio with different types of exceptions."""
    x = plan_with_ratio_exceptions if x_type == "plan" else academy_service_with_ratio_exceptions
    result_price, result_ratio = apply_pricing_ratio(price, country_code, x)
    assert result_price == expected_price
    assert result_ratio == expected_ratio


@pytest.mark.parametrize("ratio", [0.5, 0.75, 1.25, 1.5, 2.0])
def test_apply_pricing_ratio_different_ratios(ratio: float) -> None:
    """Test apply_pricing_ratio with different ratio values."""
    price = 100.0
    country_code = "test"

    # Create a mock object with pricing_ratio_exceptions
    x = MagicMock()
    x.pricing_ratio_exceptions = {"test": {"ratio": ratio}}

    result_price, result_ratio = apply_pricing_ratio(price, country_code, x)
    assert result_price == price * ratio
    assert result_ratio == ratio


@pytest.mark.parametrize("price", [99.99, 10.50, 0.99, 123.45])
def test_apply_pricing_ratio_decimal_price(price: float) -> None:
    """Test apply_pricing_ratio with decimal prices."""
    ratio = 0.8
    country_code = "test"

    # Create a mock object with pricing_ratio_exceptions
    x = MagicMock()
    x.pricing_ratio_exceptions = {"test": {"ratio": ratio}}

    result_price, result_ratio = apply_pricing_ratio(price, country_code, x)
    assert result_price == price * ratio
    assert result_ratio == ratio


def test_apply_pricing_ratio_case_insensitive(mock_general_ratios: dict) -> None:
    """Test that country codes are case insensitive."""
    price = 100
    result_lower = apply_pricing_ratio(price, "ve")
    result_upper = apply_pricing_ratio(price, "VE")
    assert result_lower == result_upper

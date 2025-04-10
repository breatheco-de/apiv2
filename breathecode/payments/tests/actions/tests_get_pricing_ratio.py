import json
from unittest.mock import MagicMock, mock_open, patch

import pytest

from breathecode.payments.actions import apply_pricing_ratio, get_pricing_ratio


@pytest.fixture
def mock_general_ratios():
    general_ratios = {"ve": 0.8, "mx": 1.0, "ar": 0.7, "br": 1.0}

    with patch("json.load", return_value=general_ratios):
        with patch("builtins.open", mock_open()) as mock_file:
            yield general_ratios


@pytest.fixture
def plan_with_ratio_exceptions():
    plan = MagicMock()
    plan.pricing_ratio_exceptions = {
        "ve": 0.7,  # Override general ratio for Venezuela
        "ar": 0.6,  # Override general ratio for Argentina
    }
    return plan


@pytest.fixture
def academy_service_with_ratio_exceptions():
    academy_service = MagicMock()
    academy_service.pricing_ratio_exceptions = {
        "ve": 0.75,  # Override general ratio for Venezuela
        "br": 0.9,  # Override general ratio for Brazil
    }
    return academy_service


def test_get_pricing_ratio_default(mock_general_ratios):
    """Test that default ratio is 1.0 when no country code is provided"""
    ratio = get_pricing_ratio(None)
    assert ratio == 1.0


def test_get_pricing_ratio_from_general_settings(mock_general_ratios):
    """Test that general pricing ratios are correctly applied"""
    ratio = get_pricing_ratio("ve")  # Venezuela has 0.8 in general settings
    assert ratio == 0.8


def test_get_pricing_ratio_plan_override(plan_with_ratio_exceptions, mock_general_ratios):
    """Test that plan-specific ratio exceptions override general settings"""
    ratio = get_pricing_ratio("ve", plan=plan_with_ratio_exceptions)
    assert ratio == 0.7  # Plan override for Venezuela


def test_get_pricing_ratio_service_override(academy_service_with_ratio_exceptions, mock_general_ratios):
    """Test that service-specific ratio exceptions override general settings"""
    ratio = get_pricing_ratio("ve", academy_service=academy_service_with_ratio_exceptions)
    assert ratio == 0.75  # Service override for Venezuela


def test_apply_pricing_ratio(mock_general_ratios):
    """Test applying pricing ratio to a price"""
    price = 100
    result = apply_pricing_ratio(price, "ve")
    assert result == 80  # 100 * 0.8


def test_apply_pricing_ratio_none_price(mock_general_ratios):
    """Test that None price returns None"""
    result = apply_pricing_ratio(None, "ve")
    assert result is None


def test_apply_pricing_ratio_no_country(mock_general_ratios):
    """Test that price is unchanged when no country code is provided"""
    price = 100
    result = apply_pricing_ratio(price, None)
    assert result == 100


def test_get_pricing_ratio_case_insensitive(mock_general_ratios):
    """Test that country codes are case insensitive"""
    ratio_lower = get_pricing_ratio("ve")
    ratio_upper = get_pricing_ratio("VE")
    assert ratio_lower == ratio_upper

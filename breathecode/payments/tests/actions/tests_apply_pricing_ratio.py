from typing import Any, Callable, Optional, Tuple, Union
from unittest.mock import MagicMock

import pytest

from breathecode.payments.actions import apply_pricing_ratio
from breathecode.payments.models import AcademyService, Plan


@pytest.fixture(autouse=True)
def mock_logger_fixture(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock the logger to prevent errors during tests."""
    mock = MagicMock()
    monkeypatch.setattr("breathecode.payments.actions.logger", mock)
    return mock


@pytest.mark.parametrize(
    "price,ratio,expected,calls_get_ratio",
    [
        (100.0, 0.8, 80.0, True),  # Basic case - calls get_pricing_ratio
        (100.0, 1.0, 100.0, True),  # Ratio is 1.0 - calls get_pricing_ratio
        (0, 0.8, 0, False),  # Zero price - doesn't call get_pricing_ratio
    ],
)
def test_apply_pricing_ratio_basic_cases(
    price: Union[float, int],
    ratio: float,
    expected: Union[float, int],
    calls_get_ratio: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test apply_pricing_ratio basic functionality with various inputs."""
    mock_get_ratio = MagicMock(return_value=ratio)
    monkeypatch.setattr("breathecode.payments.actions.get_pricing_ratio", mock_get_ratio)

    result = apply_pricing_ratio(price, "test")

    assert result == expected

    # Verify if get_pricing_ratio was called or not based on the input
    if calls_get_ratio:
        mock_get_ratio.assert_called_once_with("test", None, None)
    else:
        mock_get_ratio.assert_not_called()


def test_apply_pricing_ratio_none_price() -> None:
    """Test apply_pricing_ratio returns None if the input price is None."""
    assert apply_pricing_ratio(None, "us") is None


# Define a type for the expected_args lambda function
ArgFunction = Callable[
    [Optional[str], Optional[Any], Optional[Any]], Tuple[Optional[str], Optional[Any], Optional[Any]]
]


@pytest.mark.parametrize(
    "price,country_code,plan,service,expected_args",
    [
        (50.0, "ca", MagicMock(), None, lambda c, p, s: (c, p, None)),
        (50.0, "ca", None, MagicMock(), lambda c, p, s: (c, None, s)),
        (50.0, "ca", MagicMock(), MagicMock(), lambda c, p, s: (c, p, s)),
        (50.0, None, MagicMock(), MagicMock(), lambda c, p, s: (None, p, s)),
    ],
)
def test_apply_pricing_ratio_passes_arguments(
    price: float,
    country_code: Optional[str],
    plan: Optional[Any],
    service: Optional[Any],
    expected_args: ArgFunction,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test apply_pricing_ratio passes all arguments correctly to get_pricing_ratio."""
    mock_get_ratio = MagicMock(return_value=0.9)
    monkeypatch.setattr("breathecode.payments.actions.get_pricing_ratio", mock_get_ratio)

    result = apply_pricing_ratio(price, country_code, plan=plan, academy_service=service)

    assert result == price * 0.9
    mock_get_ratio.assert_called_once_with(*expected_args(country_code, plan, service))


@pytest.mark.parametrize("ratio", [0.5, 0.75, 1.25, 1.5, 2.0])
def test_apply_pricing_ratio_different_ratios(ratio: float, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test apply_pricing_ratio with different ratio values."""
    price = 100.0
    mock_get_ratio = MagicMock(return_value=ratio)
    monkeypatch.setattr("breathecode.payments.actions.get_pricing_ratio", mock_get_ratio)

    result = apply_pricing_ratio(price, "test")

    assert result == price * ratio
    mock_get_ratio.assert_called_once_with("test", None, None)


@pytest.mark.parametrize("price", [99.99, 10.50, 0.99, 123.45])
def test_apply_pricing_ratio_decimal_price(price: float, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test apply_pricing_ratio with decimal prices."""
    ratio = 0.8
    mock_get_ratio = MagicMock(return_value=ratio)
    monkeypatch.setattr("breathecode.payments.actions.get_pricing_ratio", mock_get_ratio)

    result = apply_pricing_ratio(price, "test")

    assert result == price * ratio
    mock_get_ratio.assert_called_once_with("test", None, None)

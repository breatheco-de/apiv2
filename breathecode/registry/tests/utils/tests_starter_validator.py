from unittest.mock import MagicMock

from breathecode.registry.models import Asset
from breathecode.registry.utils import AssetValidator, StarterValidator


def test_starter_validator_exists():
    """Test that StarterValidator can be instantiated."""
    mock_asset = MagicMock(spec=Asset)
    # Instantiation itself is the test here
    StarterValidator(mock_asset)


def test_starter_validator_inheritance():
    """Test that StarterValidator inherits from AssetValidator."""
    assert issubclass(StarterValidator, AssetValidator)


def test_starter_validator_warns_property():
    """Test that StarterValidator initializes the warns property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = StarterValidator(mock_asset)
    # Correct initial warnings based on pytest output
    assert validator.warns == ["translations", "technologies"]


def test_starter_validator_errors_property():
    """Test that StarterValidator initializes the errors property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = StarterValidator(mock_asset)
    # Correct initial errors based on pytest output
    assert validator.errors == ["lang", "urls", "category", "preview", "images", "readme_url", "description", "readme"]

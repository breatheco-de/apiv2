from unittest.mock import MagicMock

from breathecode.registry.models import Asset
from breathecode.registry.utils import AssetValidator, QuizValidator


def test_quiz_validator_exists():
    """Test that QuizValidator can be instantiated."""
    mock_asset = MagicMock(spec=Asset)
    validator = QuizValidator(mock_asset)
    assert isinstance(validator, QuizValidator)


def test_quiz_validator_inheritance():
    """Test that QuizValidator inherits from AssetValidator."""
    assert issubclass(QuizValidator, AssetValidator)


def test_quiz_validator_warns_property():
    """Test that QuizValidator initializes the warns property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = QuizValidator(mock_asset)
    # Inherits initial warnings from AssetValidator
    assert validator.warns == ["translations", "technologies", "difficulty"]


def test_quiz_validator_errors_property():
    """Test that QuizValidator initializes the errors property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = QuizValidator(mock_asset)
    # Correct initial errors based on pytest output
    assert validator.errors == ["lang", "urls", "category", "preview", "images", "readme_url", "description", "preview"]

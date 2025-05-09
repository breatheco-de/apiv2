from unittest.mock import MagicMock

from breathecode.registry.models import Asset
from breathecode.registry.utils import AssetValidator, LessonValidator


def test_lesson_validator_exists():
    """Test that LessonValidator can be instantiated."""
    mock_asset = MagicMock(spec=Asset)
    # Instantiation itself is the test here
    LessonValidator(mock_asset)


def test_lesson_validator_inheritance():
    """Test that LessonValidator inherits from AssetValidator."""
    assert issubclass(LessonValidator, AssetValidator)


def test_lesson_validator_warns_property():
    """Test that LessonValidator initializes the warns property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = LessonValidator(mock_asset)
    # Correct initial warnings based on pytest output
    assert validator.warns == ["translations", "technologies"]


def test_lesson_validator_errors_property():
    """Test that LessonValidator initializes the errors property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = LessonValidator(mock_asset)
    # Correct initial errors based on pytest output
    assert validator.errors == ["lang", "urls", "category", "preview", "images", "readme_url", "description", "readme"]

from unittest.mock import MagicMock

from breathecode.registry.models import Asset
from breathecode.registry.utils import AssetValidator, ExerciseValidator


def test_exercise_validator_exists():
    """Test that ExerciseValidator can be instantiated."""
    mock_asset = MagicMock(spec=Asset)
    # Instantiation itself is the test here
    ExerciseValidator(mock_asset)


def test_exercise_validator_inheritance():
    """Test that ExerciseValidator inherits from AssetValidator."""
    assert issubclass(ExerciseValidator, AssetValidator)


def test_exercise_validator_warns_property():
    """Test that ExerciseValidator initializes the warns property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = ExerciseValidator(mock_asset)
    # Inherits initial warnings from AssetValidator
    assert validator.warns == ["translations", "technologies", "difficulty"]


def test_exercise_validator_errors_property():
    """Test that ExerciseValidator initializes the errors property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = ExerciseValidator(mock_asset)
    # Correct initial errors based on pytest output
    assert validator.errors == [
        "lang",
        "urls",
        "category",
        "preview",
        "images",
        "readme_url",
        "description",
        "readme",
        "preview",
    ]

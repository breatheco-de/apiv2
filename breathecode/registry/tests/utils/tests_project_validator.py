from unittest.mock import MagicMock

from breathecode.registry.models import Asset
from breathecode.registry.utils import ExerciseValidator, ProjectValidator


def test_project_validator_exists():
    """Test that ProjectValidator can be instantiated."""
    mock_asset = MagicMock(spec=Asset)
    # Instantiation itself is the test here
    ProjectValidator(mock_asset)


def test_project_validator_inheritance():
    """Test that ProjectValidator inherits from ExerciseValidator."""
    assert issubclass(ProjectValidator, ExerciseValidator)


def test_project_validator_warns_property():
    """Test that ProjectValidator initializes the warns property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = ProjectValidator(mock_asset)
    # Inherits initial warnings from AssetValidator (via ExerciseValidator)
    assert validator.warns == ["translations", "technologies", "difficulty"]


def test_project_validator_errors_property():
    """Test that ProjectValidator initializes the errors property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = ProjectValidator(mock_asset)
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
        "telemetry",
    ]

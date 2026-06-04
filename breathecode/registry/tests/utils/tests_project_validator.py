from unittest.mock import MagicMock

import pytest

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
    # Correct initial errors based on pytest output (includes template_subdirectory)
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
        "template_subdirectory",
    ]


def test_template_subdirectory_raises_when_self_in_subdir():
    """When PROJECT is in subdirectory and template_url is 'self', validation errors."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.asset_type = "PROJECT"
    mock_asset.readme_url = "https://github.com/org/repo/blob/main/projects/p1/README.md"
    mock_asset.template_url = "self"
    validator = ProjectValidator(mock_asset, log_errors=False)
    with pytest.raises(Exception) as exc_info:
        validator.template_subdirectory()
    assert "cannot be 'self'" in str(exc_info.value)


def test_template_subdirectory_passes_when_not_in_subdir():
    """When PROJECT is at repo root, template_url 'self' is allowed (no error from template_subdirectory)."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.asset_type = "PROJECT"
    mock_asset.readme_url = "https://github.com/org/repo/blob/main/README.md"
    mock_asset.template_url = "self"
    validator = ProjectValidator(mock_asset, log_errors=False)
    validator.template_subdirectory()  # should not raise


def test_template_subdirectory_passes_when_url_in_subdir():
    """When PROJECT is in subdirectory and template_url is a URL, validation passes."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.asset_type = "PROJECT"
    mock_asset.readme_url = "https://github.com/org/repo/blob/main/projects/p1/README.md"
    mock_asset.template_url = "https://github.com/other/template-repo"
    validator = ProjectValidator(mock_asset, log_errors=False)
    validator.template_subdirectory()  # should not raise


def test_template_subdirectory_passes_when_empty_in_subdir():
    """When PROJECT is in subdirectory and template_url is empty, validation passes (read-only)."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.asset_type = "PROJECT"
    mock_asset.readme_url = "https://github.com/org/repo/blob/main/projects/p1/README.md"
    mock_asset.template_url = None
    validator = ProjectValidator(mock_asset, log_errors=False)
    validator.template_subdirectory()  # should not raise

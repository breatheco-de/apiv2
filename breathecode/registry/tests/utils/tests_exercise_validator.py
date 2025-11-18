from unittest.mock import MagicMock
import pytest

from breathecode.registry.models import Asset
from breathecode.registry.utils import AssetValidator, ExerciseValidator, AssetErrorLogType


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
        "telemetry",
    ]


# Telemetry validation tests


def test_telemetry_no_config():
    """Test telemetry validation when asset has no config."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.config = None
    validator = ExerciseValidator(mock_asset)
    # Should not raise any exception
    validator.telemetry()


def test_telemetry_no_telemetry_in_config():
    """Test telemetry validation when config has no telemetry field."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.config = {"slug": "test-asset"}
    validator = ExerciseValidator(mock_asset)
    # Should not raise any exception
    validator.telemetry()


def test_telemetry_no_batch_url():
    """Test telemetry validation when telemetry field has no batch URL."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.config = {"telemetry": {}}
    validator = ExerciseValidator(mock_asset)
    # Should not raise any exception
    validator.telemetry()


def test_telemetry_valid_asset_id():
    """Test telemetry validation with correct asset_id in batch URL."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = 155
    mock_asset.config = {
        "telemetry": {
            "batch": "https://breathecode.herokuapp.com/v1/assignment/me/telemetry?asset_id=155"
        }
    }
    validator = ExerciseValidator(mock_asset)
    # Should not raise any exception
    validator.telemetry()


def test_telemetry_missing_asset_id_parameter():
    """Test telemetry validation when batch URL is missing asset_id parameter."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = 155
    mock_asset.config = {
        "telemetry": {
            "batch": "https://breathecode.herokuapp.com/v1/assignment/me/telemetry"
        }
    }
    validator = ExerciseValidator(mock_asset, log_errors=False)
    
    with pytest.raises(Exception) as exc_info:
        validator.telemetry()
    
    assert "missing asset_id parameter" in str(exc_info.value).lower()


def test_telemetry_invalid_asset_id_format():
    """Test telemetry validation when asset_id is not a valid integer."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = 155
    mock_asset.config = {
        "telemetry": {
            "batch": "https://breathecode.herokuapp.com/v1/assignment/me/telemetry?asset_id=abc"
        }
    }
    validator = ExerciseValidator(mock_asset, log_errors=False)
    
    with pytest.raises(Exception) as exc_info:
        validator.telemetry()
    
    assert "invalid asset_id format" in str(exc_info.value).lower()


def test_telemetry_incorrect_asset_id():
    """Test telemetry validation when asset_id in URL doesn't match actual asset ID."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = 155
    mock_asset.config = {
        "telemetry": {
            "batch": "https://breathecode.herokuapp.com/v1/assignment/me/telemetry?asset_id=999"
        }
    }
    validator = ExerciseValidator(mock_asset, log_errors=False)
    
    with pytest.raises(Exception) as exc_info:
        validator.telemetry()
    
    error_message = str(exc_info.value).lower()
    assert "incorrect asset_id" in error_message
    assert "155" in str(exc_info.value)
    assert "999" in str(exc_info.value)


def test_telemetry_valid_with_additional_query_params():
    """Test telemetry validation with correct asset_id and additional query parameters."""
    mock_asset = MagicMock(spec=Asset)
    mock_asset.id = 155
    mock_asset.config = {
        "telemetry": {
            "batch": "https://breathecode.herokuapp.com/v1/assignment/me/telemetry?asset_id=155&other_param=value"
        }
    }
    validator = ExerciseValidator(mock_asset)
    # Should not raise any exception
    validator.telemetry()

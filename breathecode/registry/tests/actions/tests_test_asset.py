from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

# Import the function with an alias to avoid pytest conflict
from breathecode.registry.actions import test_asset as xtest_asset_action
from breathecode.registry.models import Asset
from breathecode.registry.utils import (
    ArticleValidator,
    AssetException,
    ExerciseValidator,
    LessonValidator,
    ProjectValidator,
    QuizValidator,
    StarterValidator,
)


# Mock timezone.now before importing the action
@patch("django.utils.timezone.now", MagicMock(return_value=datetime(2023, 1, 1, 12, 0, 0)))
def test_test_asset_success(db):
    """
    Test that test_asset updates status correctly on successful validation.
    """
    mock_asset = MagicMock(spec=Asset)
    mock_asset.asset_type = "LESSON"
    mock_asset.save = MagicMock()

    with patch("breathecode.registry.actions.LessonValidator") as MockValidator:
        mock_instance = MockValidator.return_value
        mock_instance.validate = MagicMock()

        result = xtest_asset_action(mock_asset)

        assert result is True
        mock_instance.validate.assert_called_once()
        assert mock_asset.status_text == "Test Successfull"
        assert mock_asset.test_status == "OK"
        assert mock_asset.last_test_at == datetime(2023, 1, 1, 12, 0, 0)
        mock_asset.save.assert_called_once()


@patch("django.utils.timezone.now", MagicMock(return_value=datetime(2023, 1, 1, 12, 0, 0)))
@pytest.mark.parametrize(
    "asset_type, ValidatorClass",
    [
        ("LESSON", LessonValidator),
        ("EXERCISE", ExerciseValidator),
        ("PROJECT", ProjectValidator),
        ("QUIZ", QuizValidator),
        ("ARTICLE", ArticleValidator),
        ("STARTER", StarterValidator),
    ],
)
def test_test_asset_success_all_types(db, asset_type, ValidatorClass):
    """
    Test successful validation across different asset types.
    """
    mock_asset = MagicMock(spec=Asset)
    mock_asset.asset_type = asset_type
    mock_asset.save = MagicMock()

    validator_path = f"breathecode.registry.actions.{ValidatorClass.__name__}"
    with patch(validator_path) as MockValidator:
        mock_instance = MockValidator.return_value
        mock_instance.validate = MagicMock()

        result = xtest_asset_action(mock_asset)

        assert result is True
        MockValidator.assert_called_once_with(mock_asset, False)
        mock_instance.validate.assert_called_once()
        assert mock_asset.status_text == "Test Successfull"
        assert mock_asset.test_status == "OK"
        assert mock_asset.last_test_at == datetime(2023, 1, 1, 12, 0, 0)
        mock_asset.save.assert_called_once()


@patch("django.utils.timezone.now", MagicMock(return_value=datetime(2023, 1, 1, 12, 0, 0)))
def test_test_asset_asset_exception(db):
    """
    Test that test_asset handles AssetException correctly.
    """
    mock_asset = MagicMock(spec=Asset)
    mock_asset.asset_type = "PROJECT"
    mock_asset.save = MagicMock()
    exception_message = "Specific validation failed"
    exception_severity = "WARNING"

    with patch("breathecode.registry.actions.ProjectValidator") as MockValidator:
        mock_instance = MockValidator.return_value
        mock_instance.validate = MagicMock(side_effect=AssetException(exception_message, severity=exception_severity))

        with pytest.raises(AssetException) as exc_info:
            xtest_asset_action(mock_asset)

        assert str(exc_info.value) == exception_message
        mock_instance.validate.assert_called_once()
        assert mock_asset.status_text == exception_message
        assert mock_asset.test_status == exception_severity
        assert mock_asset.last_test_at == datetime(2023, 1, 1, 12, 0, 0)
        mock_asset.save.assert_called_once()


@patch("django.utils.timezone.now", MagicMock(return_value=datetime(2023, 1, 1, 12, 0, 0)))
def test_test_asset_generic_exception(db):
    """
    Test that test_asset handles generic exceptions correctly.
    """
    mock_asset = MagicMock(spec=Asset)
    mock_asset.asset_type = "QUIZ"
    mock_asset.save = MagicMock()
    exception_message = "Something unexpected happened"

    with patch("breathecode.registry.actions.QuizValidator") as MockValidator:
        mock_instance = MockValidator.return_value
        mock_instance.validate = MagicMock(side_effect=Exception(exception_message))

        with pytest.raises(Exception) as exc_info:
            xtest_asset_action(mock_asset)

        assert str(exc_info.value) == exception_message
        mock_instance.validate.assert_called_once()
        assert mock_asset.status_text == exception_message
        assert mock_asset.test_status == "ERROR"
        assert mock_asset.last_test_at == datetime(2023, 1, 1, 12, 0, 0)
        mock_asset.save.assert_called_once()


@patch("django.utils.timezone.now", MagicMock(return_value=datetime(2023, 1, 1, 12, 0, 0)))
def test_test_asset_unknown_type(db):
    """
    Test that test_asset handles unknown asset types gracefully (though this scenario
    should ideally not occur if Asset.asset_type has choices enforced).
    It raises an AttributeError because no validator is instantiated.
    """
    mock_asset = MagicMock(spec=Asset)
    mock_asset.asset_type = "UNKNOWN_TYPE"
    mock_asset.save = MagicMock()

    # No validator will be patched or called for an unknown type

    with pytest.raises(AttributeError) as exc_info:
        xtest_asset_action(mock_asset)

    # It fails inside the try block, triggering the generic exception handler
    assert "'NoneType' object has no attribute 'validate'" in str(exc_info.value)
    assert mock_asset.status_text == "'NoneType' object has no attribute 'validate'"
    assert mock_asset.test_status == "ERROR"
    assert mock_asset.last_test_at == datetime(2023, 1, 1, 12, 0, 0)
    mock_asset.save.assert_called_once()  # Save IS called by the generic except block


@patch("django.utils.timezone.now", MagicMock(return_value=datetime(2023, 1, 1, 12, 0, 0)))
def test_test_asset_log_errors_true(db):
    """
    Test that log_errors=True is passed to the validator constructor.
    """
    mock_asset = MagicMock(spec=Asset)
    mock_asset.asset_type = "LESSON"
    mock_asset.save = MagicMock()

    with patch("breathecode.registry.actions.LessonValidator") as MockValidator:
        mock_instance = MockValidator.return_value
        mock_instance.validate = MagicMock()

        result = xtest_asset_action(mock_asset, log_errors=True)

        assert result is True
        # Verify log_errors=True was passed during instantiation
        MockValidator.assert_called_once_with(mock_asset, True)
        mock_instance.validate.assert_called_once()
        assert mock_asset.status_text == "Test Successfull"
        assert mock_asset.test_status == "OK"
        assert mock_asset.last_test_at == datetime(2023, 1, 1, 12, 0, 0)
        mock_asset.save.assert_called_once()

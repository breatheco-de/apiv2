from unittest.mock import MagicMock, patch

import pytest

from breathecode.registry import actions
from breathecode.registry.actions import atest_asset
from breathecode.registry.models import Asset
from breathecode.registry.utils import AssetException

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


@patch("breathecode.registry.actions.test_asset", MagicMock(return_value=True))
async def test_atest_asset_success():
    """
    Tests that atest_asset calls test_asset and returns its result (True)
    when test_asset runs successfully.
    """
    mock_asset = MagicMock(spec=Asset)
    result = await atest_asset(mock_asset)
    assert result is True
    actions.test_asset.assert_called_once_with(mock_asset, False)


@patch(
    "breathecode.registry.actions.test_asset",
    MagicMock(side_effect=AssetException("Test Error", severity="ERROR")),
)
async def test_atest_asset_asset_exception():
    """
    Tests that atest_asset propagates AssetException when test_asset raises it.
    """
    mock_asset = MagicMock(spec=Asset)
    with pytest.raises(AssetException) as exc_info:
        await atest_asset(mock_asset)

    assert str(exc_info.value) == "Test Error"
    actions.test_asset.assert_called_once_with(mock_asset, False)


@patch("breathecode.registry.actions.test_asset", MagicMock(side_effect=Exception("Generic Error")))
async def test_atest_asset_generic_exception():
    """
    Tests that atest_asset propagates generic Exceptions when test_asset raises them.
    """
    mock_asset = MagicMock(spec=Asset)
    with pytest.raises(Exception) as exc_info:
        await atest_asset(mock_asset)

    assert str(exc_info.value) == "Generic Error"
    actions.test_asset.assert_called_once_with(mock_asset, False)


@patch("breathecode.registry.actions.test_asset", MagicMock(return_value=True))
async def test_atest_asset_with_log_errors_true():
    """
    Tests that atest_asset passes log_errors=True to test_asset.
    """
    mock_asset = MagicMock(spec=Asset)
    result = await atest_asset(mock_asset, log_errors=True)
    assert result is True
    actions.test_asset.assert_called_once_with(mock_asset, True)

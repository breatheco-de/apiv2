from unittest.mock import MagicMock, patch

import pytest

from ...supervisors import check_asset_integrity


@pytest.fixture(autouse=True)
def db(db):
    yield


def test_no_issues():
    """Test supervisor when no assets have issues."""
    asset_mock = MagicMock()
    asset_mock.configure_mock(slug="ok-asset", id=1)

    asset_manager_mock = MagicMock()
    asset_manager_mock.annotate.return_value.filter.return_value = []  # No assets missing primary tech
    asset_manager_mock.filter.return_value = []  # No assets with short description

    with patch("breathecode.registry.models.Asset.objects", asset_manager_mock):
        # Call the wrapped function to test the generator logic directly
        issues = list(check_asset_integrity.__wrapped__())

    assert issues == []
    asset_manager_mock.annotate.assert_called_once()
    asset_manager_mock.filter.assert_called_once()


def test_missing_primary_tech():
    """Test supervisor when an asset is missing primary technology."""
    asset_missing_tech_mock = MagicMock()
    asset_missing_tech_mock.configure_mock(slug="no-tech-asset", id=1)

    asset_manager_mock = MagicMock()
    # Return the asset missing primary tech
    asset_manager_mock.annotate.return_value.filter.return_value = [asset_missing_tech_mock]
    # Assume this asset has a good description for the second filter
    asset_manager_mock.filter.return_value = []

    with patch("breathecode.registry.models.Asset.objects", asset_manager_mock):
        issues = list(check_asset_integrity.__wrapped__())

    assert len(issues) == 1
    # issues[0] is a tuple: (message, code, params)
    assert issues[0][1] == "asset-missing-primary-technology"  # code is at index 1
    assert issues[0][2] == {"asset_id": 1}  # params is at index 2
    asset_manager_mock.annotate.assert_called_once()
    asset_manager_mock.filter.assert_called_once()


def test_short_description():
    """Test supervisor when an asset has a short description."""
    asset_short_desc_mock = MagicMock()
    asset_short_desc_mock.configure_mock(slug="short-desc-asset", id=2)

    asset_manager_mock = MagicMock()
    # Assume no assets missing primary tech
    asset_manager_mock.annotate.return_value.filter.return_value = []
    # Return the asset with short description
    asset_manager_mock.filter.return_value = [asset_short_desc_mock]

    with patch("breathecode.registry.models.Asset.objects", asset_manager_mock):
        issues = list(check_asset_integrity.__wrapped__())

    assert len(issues) == 1
    # issues[0] is a tuple: (message, code, params)
    assert issues[0][1] == "asset-short-description"  # code is at index 1
    assert issues[0][2] == {"asset_id": 2}  # params is at index 2
    asset_manager_mock.annotate.assert_called_once()
    # The second filter is called, and the check `if asset not in assets_missing_primary_tech` passes
    asset_manager_mock.filter.assert_called_once()


def test_null_description():
    """Test supervisor when an asset has a null description."""
    asset_null_desc_mock = MagicMock()
    asset_null_desc_mock.configure_mock(slug="null-desc-asset", id=3)

    asset_manager_mock = MagicMock()
    # Assume no assets missing primary tech
    asset_manager_mock.annotate.return_value.filter.return_value = []
    # Return the asset with null description
    asset_manager_mock.filter.return_value = [asset_null_desc_mock]

    with patch("breathecode.registry.models.Asset.objects", asset_manager_mock):
        issues = list(check_asset_integrity.__wrapped__())

    assert len(issues) == 1
    # issues[0] is a tuple: (message, code, params)
    assert issues[0][1] == "asset-short-description"  # code is at index 1
    assert issues[0][2] == {"asset_id": 3}  # params is at index 2
    asset_manager_mock.annotate.assert_called_once()
    asset_manager_mock.filter.assert_called_once()


def test_both_issues_yields_only_missing_tech():
    """Test supervisor yields only missing tech issue when asset has both."""
    asset_both_issues_mock = MagicMock()
    asset_both_issues_mock.configure_mock(slug="both-issues-asset", id=4)

    asset_manager_mock = MagicMock()
    # Asset has missing primary tech
    asset_manager_mock.annotate.return_value.filter.return_value = [asset_both_issues_mock]
    # Asset also has short description, but should be ignored due to the first issue
    asset_manager_mock.filter.return_value = [asset_both_issues_mock]

    with patch("breathecode.registry.models.Asset.objects", asset_manager_mock):
        issues = list(check_asset_integrity.__wrapped__())

    assert len(issues) == 1
    # issues[0] is a tuple: (message, code, params)
    assert issues[0][1] == "asset-missing-primary-technology"  # code is at index 1
    assert issues[0][2] == {"asset_id": 4}  # params is at index 2
    asset_manager_mock.annotate.assert_called_once()
    asset_manager_mock.filter.assert_called_once()


def test_multiple_assets_different_issues():
    """Test supervisor with multiple assets having different issues."""
    asset_missing_tech_mock = MagicMock()
    asset_missing_tech_mock.configure_mock(slug="no-tech-asset", id=1)

    asset_short_desc_mock = MagicMock()
    asset_short_desc_mock.configure_mock(slug="short-desc-asset", id=2)

    asset_manager_mock = MagicMock()
    asset_manager_mock.annotate.return_value.filter.return_value = [asset_missing_tech_mock]
    asset_manager_mock.filter.return_value = [asset_short_desc_mock]

    with patch("breathecode.registry.models.Asset.objects", asset_manager_mock):
        issues = list(check_asset_integrity.__wrapped__())

    assert len(issues) == 2

    # Check presence and content of each issue type
    # issue is a tuple: (message, code, params)
    missing_tech_issue = next((i for i in issues if i[1] == "asset-missing-primary-technology"), None)
    short_desc_issue = next((i for i in issues if i[1] == "asset-short-description"), None)

    assert missing_tech_issue is not None
    assert missing_tech_issue[2] == {"asset_id": 1}  # params is at index 2

    assert short_desc_issue is not None
    assert short_desc_issue[2] == {"asset_id": 2}  # params is at index 2

    asset_manager_mock.annotate.assert_called_once()
    asset_manager_mock.filter.assert_called_once()

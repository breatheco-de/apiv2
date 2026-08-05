from unittest.mock import patch

import pytest

from breathecode.registry.actions import invalidate_asset_caches_after_sync, pull_from_github


def test_invalidate_asset_caches_after_sync_clears_api_and_schedules_frontend():
    with (
        patch("breathecode.registry.caches.AssetCache.clear") as clear_mock,
        patch("breathecode.registry.tasks.async_update_frontend_asset_cache.delay") as frontend_mock,
    ):
        invalidate_asset_caches_after_sync("my-lesson")

    clear_mock.assert_called_once_with()
    frontend_mock.assert_called_once_with("my-lesson")


@pytest.mark.django_db
def test_pull_from_github_invalidates_cache_on_successful_external_readme(bc):
    model = bc.database.create(
        asset={
            "slug": "external-lesson",
            "asset_type": "LESSON",
            "readme_url": "https://example.com/readme.md",
        }
    )

    with (
        patch("breathecode.registry.actions.generate_external_readme", return_value=True),
        patch("breathecode.registry.actions.invalidate_asset_caches_after_sync") as invalidate_mock,
    ):
        result = pull_from_github(model.asset.slug)

    assert result == "OK"
    invalidate_mock.assert_called_once_with(model.asset.slug)


@pytest.mark.django_db
def test_pull_from_github_does_not_invalidate_cache_when_asset_missing():
    with patch("breathecode.registry.actions.invalidate_asset_caches_after_sync") as invalidate_mock:
        result = pull_from_github("does-not-exist")

    assert result == "ERROR"
    invalidate_mock.assert_not_called()

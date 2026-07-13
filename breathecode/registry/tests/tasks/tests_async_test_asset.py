from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.utils import timezone

from breathecode.registry.tasks import async_test_asset


@patch("breathecode.registry.tasks.test_asset", MagicMock(return_value=True))
def test_async_test_asset_runs_when_never_tested(db):
    from breathecode.registry.models import Asset

    asset = Asset.objects.create(
        slug="never-tested",
        asset_type="ARTICLE",
        title="Never tested",
    )

    result = async_test_asset(asset.slug)

    assert result is True
    from breathecode.registry import tasks

    tasks.test_asset.assert_called_once()


@patch("breathecode.registry.tasks.test_asset", MagicMock(return_value=True))
def test_async_test_asset_skips_when_recently_tested(db):
    from breathecode.registry.models import Asset

    asset = Asset.objects.create(
        slug="recently-tested",
        asset_type="ARTICLE",
        title="Recently tested",
        test_status="OK",
        last_test_at=timezone.now() - timedelta(days=1),
    )

    result = async_test_asset(asset.slug)

    assert result is True
    from breathecode.registry import tasks

    tasks.test_asset.assert_not_called()


@patch("breathecode.registry.tasks.test_asset", MagicMock(return_value=True))
def test_async_test_asset_reruns_when_force_true(db):
    from breathecode.registry.models import Asset

    asset = Asset.objects.create(
        slug="force-retest",
        asset_type="ARTICLE",
        title="Force retest",
        test_status="OK",
        last_test_at=timezone.now() - timedelta(days=1),
    )

    result = async_test_asset(asset.slug, force=True)

    assert result is True
    from breathecode.registry import tasks

    tasks.test_asset.assert_called_once()

import pytest
from django.contrib.auth.models import User

from breathecode.registry.models import Asset, AssetErrorLog


@pytest.mark.django_db
def test_asset_log_error_dedups_identical_entries():
    asset = Asset.objects.create(
        slug="dedup-project",
        title="Dedup Project",
        asset_type="PROJECT",
        lang="us",
        preview="https://example.com/preview.png",
    )

    asset.log_error("missing-preview", "first")
    asset.log_error("missing-preview", "second")

    items = AssetErrorLog.objects.filter(
        slug="missing-preview",
        asset=asset,
        asset_type="PROJECT",
        path=asset.slug,
    )
    assert items.count() == 1
    assert items.first().status_text == "second"


@pytest.mark.django_db
def test_log_once_dedups_when_asset_is_null():
    AssetErrorLog.log_once(slug="slug-not-found", path="missing-asset", asset_type="PROJECT", status_text="one")
    AssetErrorLog.log_once(slug="slug-not-found", path="missing-asset", asset_type="PROJECT", status_text="two")

    items = AssetErrorLog.objects.filter(slug="slug-not-found", path="missing-asset", asset__isnull=True)
    assert items.count() == 1
    assert items.first().status_text == "two"


@pytest.mark.django_db
def test_log_once_dedups_when_users_differ():
    asset = Asset.objects.create(
        slug="same-asset",
        title="Same Asset",
        asset_type="LESSON",
        lang="us",
        preview="https://example.com/preview.png",
    )
    user_one = User.objects.create_user(username="dedup-user-1", email="dedup-user-1@example.com", password="123456")
    user_two = User.objects.create_user(username="dedup-user-2", email="dedup-user-2@example.com", password="123456")

    AssetErrorLog.log_once(
        slug="invalid-url",
        path=asset.slug,
        asset=asset,
        asset_type=asset.asset_type,
        user=user_one,
        status_text="first",
    )
    AssetErrorLog.log_once(
        slug="invalid-url",
        path=asset.slug,
        asset=asset,
        asset_type=asset.asset_type,
        user=user_two,
        status_text="second",
    )

    items = AssetErrorLog.objects.filter(slug="invalid-url", path=asset.slug, asset=asset, asset_type=asset.asset_type)
    assert items.count() == 1
    assert items.first().user_id == user_two.id


@pytest.mark.django_db
def test_log_once_sets_error_status_after_fixed():
    asset = Asset.objects.create(
        slug="status-reset",
        title="Status Reset",
        asset_type="EXERCISE",
        lang="us",
        preview="https://example.com/preview.png",
    )

    log = AssetErrorLog.log_once(
        slug="invalid-readme",
        path=asset.slug,
        asset=asset,
        asset_type=asset.asset_type,
        status_text="old",
    )
    log.status = "FIXED"
    log.save(update_fields=["status"])

    AssetErrorLog.log_once(
        slug="invalid-readme",
        path=asset.slug,
        asset=asset,
        asset_type=asset.asset_type,
        status_text="new",
    )

    updated = AssetErrorLog.objects.get(id=log.id)
    assert updated.status == "ERROR"
    assert updated.status_text == "new"

import capyc.pytest as capy

from breathecode.services.learnpack.client import LearnPack


def test_add_webhook_to_log_sets_nullable_ids_when_values_are_numeric(database: capy.Database):
    model = database.create(asset={"slug": "logged-asset", "lang": "us", "asset_type": "EXERCISE"})
    asset_id = model.asset.id
    payload = {
        "event": "batch",
        "user_id": 1,
        "slug": "my-asset",
        "package_slug": "my-package",
        "asset_id": str(asset_id),
        "package_id": "9876543210",
    }

    webhook = LearnPack.add_webhook_to_log(payload)

    assert webhook is not None
    assert webhook.asset_id == asset_id
    assert webhook.learnpack_package_id == 9876543210
    assert webhook.package_slug == "my-package"


def test_add_webhook_to_log_sets_null_ids_when_values_are_invalid(database: capy.Database):
    payload = {
        "event": "batch",
        "user_id": 1,
        "slug": "my-asset",
        "asset_id": "abc",
        "package_id": "nope",
    }

    webhook = LearnPack.add_webhook_to_log(payload)

    assert webhook is not None
    assert webhook.asset_id is None
    assert webhook.learnpack_package_id is None
    assert webhook.package_slug == "my-asset"


def test_add_webhook_to_log_resolves_csv_asset_id_to_english_candidate(database: capy.Database):
    model = database.create(
        asset=[
            {"slug": "csv-es", "lang": "es", "asset_type": "EXERCISE"},
            {"slug": "csv-us", "lang": "us", "asset_type": "EXERCISE"},
        ],
    )
    es_asset, us_asset = model.asset
    payload = {
        "event": "batch",
        "user_id": 1,
        "slug": "my-asset",
        "asset_id": f"{es_asset.id},{us_asset.id}",
        "package_id": "1",
    }
    webhook = LearnPack.add_webhook_to_log(payload)
    assert webhook.asset_id == us_asset.id

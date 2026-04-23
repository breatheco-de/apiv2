import capyc.pytest as capy

from breathecode.assignments.management.commands.backfill_learnpack_webhook_payload_fields import Command


def test_backfill_webhook_payload_fields_dry_run_does_not_persist(database: capy.Database):
    model = database.create(
        asset={"slug": "dry-asset", "lang": "us", "asset_type": "EXERCISE"},
        learn_pack_webhook={
            "payload": {},
            "asset_id": None,
            "learnpack_package_id": None,
            "package_slug": None,
        },
    )
    webhook = model.learn_pack_webhook
    webhook.payload = {
        "asset_id": str(model.asset.id),
        "package_id": "456",
        "package_slug": "pkg-slug",
    }
    webhook.save()

    Command().handle(dry_run=True, overwrite=False)
    model.learn_pack_webhook.refresh_from_db()

    assert model.learn_pack_webhook.asset_id is None
    assert model.learn_pack_webhook.learnpack_package_id is None
    assert model.learn_pack_webhook.package_slug is None


def test_backfill_webhook_payload_fields_populates_missing_values(database: capy.Database):
    model = database.create(
        asset={"slug": "fill-asset", "lang": "us", "asset_type": "EXERCISE"},
        learn_pack_webhook={
            "payload": {},
            "asset_id": None,
            "learnpack_package_id": None,
            "package_slug": None,
        },
    )
    aid = model.asset.id
    webhook = model.learn_pack_webhook
    webhook.payload = {"asset_id": str(aid), "package_id": "456", "slug": "pkg-from-slug"}
    webhook.save()

    Command().handle(dry_run=False, overwrite=False)
    model.learn_pack_webhook.refresh_from_db()

    assert model.learn_pack_webhook.asset_id == aid
    assert model.learn_pack_webhook.learnpack_package_id == 456
    assert model.learn_pack_webhook.package_slug == "pkg-from-slug"


def test_backfill_webhook_payload_fields_overwrite_updates_existing_values(database: capy.Database):
    model = database.create(
        asset={"slug": "ow-asset", "lang": "us", "asset_type": "EXERCISE"},
        learn_pack_webhook={
            "payload": {},
            "asset_id": 1,
            "learnpack_package_id": 2,
            "package_slug": "pkg-old",
        },
    )
    aid = model.asset.id
    webhook = model.learn_pack_webhook
    webhook.payload = {"asset_id": str(aid), "package_id": "654", "package_slug": "pkg-new"}
    webhook.save()

    Command().handle(dry_run=False, overwrite=True)
    model.learn_pack_webhook.refresh_from_db()

    assert model.learn_pack_webhook.asset_id == aid
    assert model.learn_pack_webhook.learnpack_package_id == 654
    assert model.learn_pack_webhook.package_slug == "pkg-new"


def test_backfill_csv_asset_id_prefers_english_candidate(database: capy.Database):
    model = database.create(
        asset=[
            {"slug": "bf-es", "lang": "es", "asset_type": "EXERCISE"},
            {"slug": "bf-us", "lang": "us", "asset_type": "EXERCISE"},
        ],
        learn_pack_webhook={
            "payload": {},
            "asset_id": None,
            "learnpack_package_id": None,
            "package_slug": None,
        },
    )
    es_asset, us_asset = model.asset
    webhook = model.learn_pack_webhook
    webhook.payload = {"asset_id": f"{es_asset.id},{us_asset.id}", "package_id": "1"}
    webhook.save()

    Command().handle(dry_run=False, overwrite=False)
    webhook.refresh_from_db()

    assert webhook.asset_id == us_asset.id

import capyc.pytest as capy

from breathecode.assignments.management.commands.backfill_learnpack_webhook_payload_fields import Command


def test_backfill_webhook_payload_fields_dry_run_does_not_persist(database: capy.Database):
    model = database.create(
        learn_pack_webhook={
            "payload": {"asset_id": "123", "package_id": "456", "package_slug": "pkg-slug"},
            "asset_id": None,
            "learnpack_package_id": None,
            "package_slug": None,
        }
    )

    Command().handle(dry_run=True, overwrite=False)
    model.learn_pack_webhook.refresh_from_db()

    assert model.learn_pack_webhook.asset_id is None
    assert model.learn_pack_webhook.learnpack_package_id is None
    assert model.learn_pack_webhook.package_slug is None


def test_backfill_webhook_payload_fields_populates_missing_values(database: capy.Database):
    model = database.create(
        learn_pack_webhook={
            "payload": {"asset_id": "123", "package_id": "456", "slug": "pkg-from-slug"},
            "asset_id": None,
            "learnpack_package_id": None,
            "package_slug": None,
        }
    )

    Command().handle(dry_run=False, overwrite=False)
    model.learn_pack_webhook.refresh_from_db()

    assert model.learn_pack_webhook.asset_id == 123
    assert model.learn_pack_webhook.learnpack_package_id == 456
    assert model.learn_pack_webhook.package_slug == "pkg-from-slug"


def test_backfill_webhook_payload_fields_overwrite_updates_existing_values(database: capy.Database):
    model = database.create(
        learn_pack_webhook={
            "payload": {"asset_id": "987", "package_id": "654", "package_slug": "pkg-new"},
            "asset_id": 1,
            "learnpack_package_id": 2,
            "package_slug": "pkg-old",
        }
    )

    Command().handle(dry_run=False, overwrite=True)
    model.learn_pack_webhook.refresh_from_db()

    assert model.learn_pack_webhook.asset_id == 987
    assert model.learn_pack_webhook.learnpack_package_id == 654
    assert model.learn_pack_webhook.package_slug == "pkg-new"

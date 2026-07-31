import capyc.pytest as capy

from breathecode.registry.models import Asset
from breathecode.services.learnpack.actions.package_manifest_updated import package_manifest_updated
from breathecode.services.learnpack.client import LearnPack


def test_package_manifest_updated_sets_manifest_only(database: capy.Database):
    model = database.create(
        asset={
            "slug": "pkg-manifest-1",
            "lang": "us",
            "asset_type": "EXERCISE",
            "learnpack_id": 15598,
            "learnpack_deploy_url": "https://old.example.com",
            "config": {"slug": "pkg-manifest-1", "title": "Keep Me"},
            "title": "Keep Me",
        },
        learn_pack_webhook=1,
    )

    webhook = model.learn_pack_webhook
    webhook.event = "package_manifest_updated"
    webhook.payload = {
        "event": "package_manifest_updated",
        "package_slug": model.asset.slug,
        "package_id": 15598,
        "payload": {
            "package": {
                "id": 15598,
                "package_slug": model.asset.slug,
                "asset_ids": [model.asset.id],
                "custom_deployment_url": "https://should-not-apply.example.com",
                "deployment_url": "https://also-should-not-apply.example.com",
                "config": '{"slug":"pkg-manifest-1","title":"Do Not Apply"}',
            },
            "manifest": {
                "schemaVersion": 1,
                "slug": "pkg-manifest-1",
                "lessons": [{"id": "00.0", "slug": "welcome", "position": 0, "type": "READ"}],
            },
        },
    }
    webhook.save()

    package_manifest_updated(None, webhook)

    asset = Asset.objects.get(id=model.asset.id)
    assert asset.manifest["schemaVersion"] == 1
    assert asset.manifest["slug"] == "pkg-manifest-1"
    assert asset.learnpack_id == 15598
    assert asset.learnpack_deploy_url == "https://old.example.com"
    assert asset.title == "Keep Me"
    assert asset.config["title"] == "Keep Me"


def test_package_manifest_updated_updates_all_asset_ids(database: capy.Database):
    model = database.create(
        asset=[
            {"slug": "pkg-manifest-us", "lang": "us", "asset_type": "EXERCISE"},
            {"slug": "pkg-manifest-es", "lang": "es", "asset_type": "EXERCISE"},
        ],
        learn_pack_webhook=1,
    )

    us_asset, es_asset = model.asset
    webhook = model.learn_pack_webhook
    webhook.event = "package_manifest_updated"
    webhook.payload = {
        "event": "package_manifest_updated",
        "package_slug": us_asset.slug,
        "package_id": 99,
        "payload": {
            "package": {
                "id": 99,
                "asset_ids": [us_asset.id, es_asset.id],
            },
            "manifest": {"schemaVersion": 2, "slug": "pkg-manifest-us"},
        },
    }
    webhook.save()

    package_manifest_updated(None, webhook)

    us_asset = Asset.objects.get(id=us_asset.id)
    es_asset = Asset.objects.get(id=es_asset.id)
    assert us_asset.manifest["schemaVersion"] == 2
    assert es_asset.manifest["schemaVersion"] == 2
    assert us_asset.learnpack_id is None
    assert es_asset.learnpack_id is None


def test_package_manifest_updated_raises_without_manifest(database: capy.Database):
    model = database.create(
        asset={"slug": "pkg-manifest-missing", "lang": "us", "asset_type": "EXERCISE"},
        learn_pack_webhook=1,
    )

    webhook = model.learn_pack_webhook
    webhook.event = "package_manifest_updated"
    webhook.payload = {
        "event": "package_manifest_updated",
        "package_slug": model.asset.slug,
        "package_id": 1,
        "payload": {"package": {"id": 1, "asset_ids": [model.asset.id]}},
    }
    webhook.save()

    try:
        package_manifest_updated(None, webhook)
        assert False, "expected Exception"
    except Exception as e:
        assert "manifest" in str(e).lower()


def test_execute_action_package_manifest_updated(database: capy.Database):
    model = database.create(
        asset={"slug": "pkg-manifest-exec", "lang": "us", "asset_type": "EXERCISE"},
        learn_pack_webhook=1,
    )

    webhook = model.learn_pack_webhook
    webhook.event = "package_manifest_updated"
    webhook.payload = {
        "event": "package_manifest_updated",
        "package_slug": model.asset.slug,
        "package_id": 42,
        "payload": {
            "package": {"id": 42, "asset_ids": [model.asset.id]},
            "manifest": {"schemaVersion": 1, "slug": "pkg-manifest-exec"},
        },
    }
    webhook.status = "PENDING"
    webhook.save()

    LearnPack().execute_action(webhook.id)

    webhook.refresh_from_db()
    asset = Asset.objects.get(id=model.asset.id)

    assert webhook.status == "DONE"
    assert asset.manifest["slug"] == "pkg-manifest-exec"

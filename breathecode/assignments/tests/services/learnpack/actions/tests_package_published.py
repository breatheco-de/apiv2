import json

import capyc.pytest as capy

from breathecode.registry.models import Asset
from breathecode.services.learnpack.actions.batch import batch
from breathecode.services.learnpack.actions.package_published import package_published
from breathecode.services.learnpack.client import LearnPack


def test_package_published_sets_learnpack_id_and_deploy_url(database: capy.Database):
    model = database.create(
        asset={"slug": "pkg-pub-1", "lang": "us", "asset_type": "EXERCISE"},
        learn_pack_webhook=1,
    )

    webhook = model.learn_pack_webhook
    webhook.event = "package_published"
    webhook.payload = {
        "event": "package_published",
        "slug": model.asset.slug,
        "package_id": 999001,
        "payload": {
            "package": {
                "id": 999001,
                "asset_id": [model.asset.id],
                "deployment_url": "https://learnpack.cloud/deploy/pkg-pub-1",
            }
        },
    }
    webhook.save()

    package_published(None, webhook)

    asset = Asset.objects.get(id=model.asset.id)
    assert asset.learnpack_id == 999001
    assert asset.learnpack_deploy_url == "https://learnpack.cloud/deploy/pkg-pub-1"


def test_package_published_prefers_custom_deployment_url(database: capy.Database):
    model = database.create(
        asset={"slug": "pkg-pub-2", "lang": "us", "asset_type": "EXERCISE", "learnpack_id": 10},
        learn_pack_webhook=1,
    )

    webhook = model.learn_pack_webhook
    webhook.event = "package_published"
    webhook.payload = {
        "event": "package_published",
        "package_slug": model.asset.slug,
        "payload": {
            "package": {
                "id": 10,
                "asset_id": [model.asset.id],
                "custom_deployment_url": "https://custom.example.com/deploy",
                "deployment_url": "https://learnpack.cloud/deploy/alt",
            }
        },
    }
    webhook.save()

    package_published(None, webhook)

    asset = Asset.objects.get(id=model.asset.id)
    assert asset.learnpack_id == 10
    assert asset.learnpack_deploy_url == "https://custom.example.com/deploy"


def test_package_published_no_op_when_fields_unchanged(database: capy.Database):
    model = database.create(
        asset={
            "slug": "pkg-pub-3",
            "lang": "us",
            "asset_type": "EXERCISE",
            "learnpack_id": 55,
            "learnpack_deploy_url": "https://learnpack.cloud/deploy/same",
        },
        learn_pack_webhook=1,
    )

    webhook = model.learn_pack_webhook
    webhook.event = "package_published"
    webhook.payload = {
        "event": "package_published",
        "package_id": 55,
        "slug": model.asset.slug,
        "payload": {
            "package": {
                "id": 55,
                "deployment_url": "https://learnpack.cloud/deploy/same",
            }
        },
    }
    webhook.save()

    package_published(None, webhook)

    asset = Asset.objects.get(id=model.asset.id)
    assert asset.learnpack_id == 55
    assert asset.learnpack_deploy_url == "https://learnpack.cloud/deploy/same"


def test_package_published_resolves_by_existing_learnpack_id(database: capy.Database):
    model = database.create(
        asset={
            "slug": "pkg-pub-4",
            "lang": "us",
            "asset_type": "EXERCISE",
            "learnpack_id": 777,
        },
        learn_pack_webhook=1,
    )

    webhook = model.learn_pack_webhook
    webhook.event = "package_published"
    webhook.payload = {
        "event": "package_published",
        "package_id": 777,
        "package_slug": model.asset.slug,
        "payload": {
            "package": {
                "id": 777,
                "deployment_url": "https://learnpack.cloud/deploy/by-id",
            }
        },
    }
    webhook.save()

    package_published(None, webhook)

    asset = Asset.objects.get(id=model.asset.id)
    assert asset.learnpack_deploy_url == "https://learnpack.cloud/deploy/by-id"


def test_package_published_raises_when_asset_missing(database: capy.Database):
    model = database.create(learn_pack_webhook=1)

    webhook = model.learn_pack_webhook
    webhook.event = "package_published"
    webhook.payload = {
        "event": "package_published",
        "slug": "does-not-exist",
        "package_id": 1,
        "payload": {
            "package": {
                "id": 1,
                "deployment_url": "https://example.com",
            }
        },
    }
    webhook.save()

    try:
        package_published(None, webhook)
        assert False, "expected Exception"
    except Exception as e:
        assert "not found" in str(e).lower()


def test_package_published_updates_all_comma_separated_asset_ids(database: capy.Database):
    model = database.create(
        asset=[
            {"slug": "pkg-pub-csv-us", "lang": "us", "asset_type": "EXERCISE"},
            {"slug": "pkg-pub-csv-es", "lang": "es", "asset_type": "EXERCISE"},
        ],
        learn_pack_webhook=1,
    )

    us_asset, es_asset = model.asset
    webhook = model.learn_pack_webhook
    webhook.event = "package_published"
    webhook.payload = {
        "event": "package_published",
        "slug": us_asset.slug,
        "package_id": 888001,
        "payload": {
            "package": {
                "id": 888001,
                "asset_id": f"{es_asset.id},{us_asset.id}",
                "deployment_url": "https://learnpack.cloud/deploy/csv",
            }
        },
    }
    webhook.save()

    package_published(None, webhook)

    us_asset = Asset.objects.get(id=us_asset.id)
    es_asset = Asset.objects.get(id=es_asset.id)
    assert us_asset.learnpack_id == 888001
    assert es_asset.learnpack_id == 888001
    assert us_asset.learnpack_deploy_url == "https://learnpack.cloud/deploy/csv"
    assert es_asset.learnpack_deploy_url == "https://learnpack.cloud/deploy/csv"


def test_package_published_reads_nested_package_asset_id_list(database: capy.Database):
    model = database.create(
        asset=[
            {"slug": "pkg-pub-nested-us", "lang": "us", "asset_type": "EXERCISE"},
            {"slug": "pkg-pub-nested-es", "lang": "es", "asset_type": "EXERCISE"},
        ],
        learn_pack_webhook=1,
    )

    us_asset, es_asset = model.asset
    webhook = model.learn_pack_webhook
    webhook.event = "package_published"
    webhook.payload = {
        "event": "package_published",
        "package_slug": us_asset.slug,
        "package_id": 15598,
        "payload": {
            "package": {
                "id": 15598,
                "package_slug": us_asset.slug,
                "asset_id": [es_asset.id, us_asset.id],
                "custom_deployment_url": None,
                "deployment_url": "https://model-health-monitoring.learn-pack.com",
                "config": json.dumps(
                    {
                        "slug": "pkg-pub-nested-us",
                        "title": {"en": "Nested Title", "es": "Titulo Nested"},
                        "preview": "https://example.com/preview.png",
                        "difficulty": "beginner",
                        "technologies": ["python"],
                    }
                ),
            },
            "manifest": {
                "schemaVersion": 1,
                "slug": "pkg-pub-nested-us",
                "lessons": [{"id": "00.0", "slug": "welcome", "position": 0, "type": "READ"}],
            },
        },
    }
    webhook.save()

    package_published(None, webhook)

    us_asset = Asset.objects.get(id=us_asset.id)
    es_asset = Asset.objects.get(id=es_asset.id)
    assert us_asset.learnpack_id == 15598
    assert es_asset.learnpack_id == 15598
    assert us_asset.learnpack_deploy_url == "https://model-health-monitoring.learn-pack.com"
    assert es_asset.learnpack_deploy_url == "https://model-health-monitoring.learn-pack.com"
    assert us_asset.manifest["schemaVersion"] == 1
    assert es_asset.manifest["slug"] == "pkg-pub-nested-us"
    assert us_asset.config["preview"] == "https://example.com/preview.png"
    assert us_asset.title == "Nested Title"
    assert es_asset.title == "Titulo Nested"


def test_package_published_skips_apply_learn_config_when_config_unchanged(database: capy.Database):
    config = {
        "slug": "pkg-pub-same-config",
        "title": "Same Config",
        "preview": "https://example.com/p.png",
        "difficulty": "BEGINNER",
        "technologies": [],
    }
    model = database.create(
        asset={
            "slug": "pkg-pub-same-config",
            "lang": "us",
            "asset_type": "EXERCISE",
            "title": "Same Config",
            "config": config,
            "preview": "https://example.com/p.png",
        },
        learn_pack_webhook=1,
    )

    webhook = model.learn_pack_webhook
    webhook.event = "package_published"
    webhook.payload = {
        "event": "package_published",
        "package_slug": model.asset.slug,
        "package_id": 42,
        "payload": {
            "package": {
                "id": 42,
                "asset_id": [model.asset.id],
                "deployment_url": "https://example.com/deploy",
                "config": json.dumps(config),
            },
            "manifest": {"schemaVersion": 1, "slug": "pkg-pub-same-config"},
        },
    }
    webhook.save()

    package_published(None, webhook)

    asset = Asset.objects.get(id=model.asset.id)
    assert asset.learnpack_id == 42
    assert asset.manifest["schemaVersion"] == 1
    assert asset.title == "Same Config"
    assert asset.config == config


def test_execute_action_package_published_without_user_id(database: capy.Database):
    model = database.create(
        asset={"slug": "pkg-pub-exec", "lang": "us", "asset_type": "EXERCISE"},
        learn_pack_webhook=1,
    )

    webhook = model.learn_pack_webhook
    webhook.event = "package_published"
    webhook.payload = {
        "event": "package_published",
        "slug": model.asset.slug,
        "package_id": 4242,
        "payload": {
            "package": {
                "id": 4242,
                "asset_id": [model.asset.id],
                "deployment_url": "https://learnpack.cloud/deploy/exec",
            }
        },
    }
    webhook.status = "PENDING"
    webhook.save()

    LearnPack().execute_action(webhook.id)

    webhook.refresh_from_db()
    asset = Asset.objects.get(id=model.asset.id)

    assert webhook.status == "DONE"
    assert asset.learnpack_id == 4242
    assert asset.learnpack_deploy_url == "https://learnpack.cloud/deploy/exec"


def test_batch_requires_user_id(database: capy.Database):
    model = database.create(
        asset={"slug": "batch-needs-user", "lang": "us", "asset_type": "EXERCISE"},
        learn_pack_webhook=1,
    )

    webhook = model.learn_pack_webhook
    webhook.student = None
    webhook.payload = {"event": "batch", "asset_id": model.asset.id}
    webhook.save()

    try:
        batch(None, webhook)
        assert False, "expected Exception"
    except Exception as e:
        assert "user id" in str(e).lower()

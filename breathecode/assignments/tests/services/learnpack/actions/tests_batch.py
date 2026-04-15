import capyc.pytest as capy

from breathecode.assignments.models import AssignmentTelemetry, Task
from breathecode.services.learnpack.actions.batch import batch


def test_batch_uses_canonical_translation_slug_for_telemetry(database: capy.Database):
    model = database.create(
        user=1,
        asset=[
            {"slug": "exercise-us", "lang": "us", "asset_type": "EXERCISE"},
            {"slug": "exercise-es", "lang": "es", "asset_type": "EXERCISE"},
        ],
        task={"associated_slug": "exercise-us", "task_type": "EXERCISE", "user": 1, "title": "Exercise"},
        learn_pack_webhook=1,
    )

    canonical_asset = model.asset[0]
    secondary_asset = model.asset[1]
    secondary_asset.all_translations.add(canonical_asset)

    webhook = model.learn_pack_webhook
    webhook.student = model.user
    webhook.payload = {"asset_id": secondary_asset.id, "user_id": model.user.id, "event": "batch"}
    webhook.save()

    batch(None, webhook)

    telemetry = AssignmentTelemetry.objects.filter(user=model.user).first()
    task = Task.objects.get(id=model.task.id)

    assert telemetry is not None
    assert telemetry.asset_slug == canonical_asset.slug
    assert task.telemetry_id == telemetry.id


def test_batch_merges_telemetry_updates_from_translation_ids(database: capy.Database):
    model = database.create(
        user=1,
        asset=[
            {"slug": "exercise-us-2", "lang": "us", "asset_type": "EXERCISE"},
            {"slug": "exercise-es-2", "lang": "es", "asset_type": "EXERCISE"},
        ],
        task={"associated_slug": "exercise-us-2", "task_type": "EXERCISE", "user": 1, "title": "Exercise"},
        learn_pack_webhook=2,
    )

    canonical_asset = model.asset[0]
    secondary_asset = model.asset[1]
    secondary_asset.all_translations.add(canonical_asset)

    webhook_one = model.learn_pack_webhook[0]
    webhook_one.student = model.user
    webhook_one.payload = {"asset_id": secondary_asset.id, "user_id": model.user.id, "event": "batch", "step": 1}
    webhook_one.save()

    webhook_two = model.learn_pack_webhook[1]
    webhook_two.student = model.user
    webhook_two.payload = {"asset_id": canonical_asset.id, "user_id": model.user.id, "event": "batch", "step": 2}
    webhook_two.save()

    batch(None, webhook_one)
    batch(None, webhook_two)

    rows = AssignmentTelemetry.objects.filter(user=model.user)
    telemetry = rows.first()

    assert rows.count() == 1
    assert telemetry.asset_slug == canonical_asset.slug
    assert telemetry.telemetry["step"] == 2

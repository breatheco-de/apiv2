import capyc.pytest as capy

from breathecode.assignments.management.commands.reconcile_canonical_telemetry import Command
from breathecode.assignments.models import AssignmentTelemetry, Task
from breathecode.registry.models import Asset


def _build_translation_assets():
    canonical = Asset.objects.create(slug="canonical-us", lang="us", asset_type="EXERCISE", title="Canonical")
    translated = Asset.objects.create(slug="canonical-es", lang="es", asset_type="EXERCISE", title="Translated")
    translated.all_translations.add(canonical)
    return canonical, translated


def test_reconcile_canonical_telemetry_dry_run_does_not_write(database: capy.Database):
    model = database.create(user=1)
    canonical, translated = _build_translation_assets()
    telemetry = AssignmentTelemetry.objects.create(user=model.user, asset_slug=translated.slug, telemetry={"step": 1})
    task = Task.objects.create(
        user=model.user,
        associated_slug=canonical.slug,
        task_type="EXERCISE",
        title="Exercise",
        telemetry=telemetry,
    )

    Command().handle(dry_run=True)

    telemetry.refresh_from_db()
    task.refresh_from_db()

    assert telemetry.asset_slug == translated.slug
    assert AssignmentTelemetry.objects.filter(user=model.user).count() == 1
    assert task.telemetry_id == telemetry.id


def test_reconcile_canonical_telemetry_merges_rows_and_repoints_tasks(database: capy.Database):
    model = database.create(user=1)
    canonical, translated = _build_translation_assets()

    old_row = AssignmentTelemetry.objects.create(user=model.user, asset_slug=translated.slug, telemetry={"step": 1})
    canonical_row = AssignmentTelemetry.objects.create(user=model.user, asset_slug=canonical.slug, telemetry={"step": 2})

    task = Task.objects.create(
        user=model.user,
        associated_slug=canonical.slug,
        task_type="EXERCISE",
        title="Exercise",
        telemetry=old_row,
    )

    Command().handle(dry_run=False)

    task.refresh_from_db()
    rows = AssignmentTelemetry.objects.filter(user=model.user)

    assert rows.count() == 1
    final_row = rows.first()
    assert final_row.asset_slug == canonical.slug
    assert final_row.telemetry["step"] in [1, 2]
    assert task.telemetry_id == final_row.id
    assert not AssignmentTelemetry.objects.filter(id=old_row.id).exists() or final_row.id == old_row.id
    assert not AssignmentTelemetry.objects.filter(id=canonical_row.id).exists() or final_row.id == canonical_row.id

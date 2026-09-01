import logging
from collections import Counter

from breathecode.assignments.actions import calculate_telemetry_indicator
from breathecode.assignments.models import AssignmentTelemetry, LearnPackWebhook

logger = logging.getLogger(__name__)


def batch(self, webhook: LearnPackWebhook):
    # lazyload to fix circular import
    from breathecode.assignments.models import Task
    from breathecode.registry.models import Asset
    from breathecode.services.learnpack.resolve_payload_asset import (
        collect_learnpack_candidate_assets,
        translation_slugs_for_asset,
    )

    payload = webhook.payload or {}
    if "user_id" not in payload:
        raise Exception("Impossible to retrive learnpack user id")
    if webhook.student is None:
        raise Exception(f"Learnpack student with user id {payload['user_id']} not found")

    logger.info(
        "learnpack batch start student_id=%s payload_user_id=%s",
        webhook.student.id,
        payload.get("user_id"),
    )

    candidates = collect_learnpack_candidate_assets(payload)
    if not candidates:
        logger.warning("learnpack batch abort no candidate assets student_id=%s", webhook.student.id)
        raise Exception(
            "Asset specified by learnpack telemetry was not found using either the payload 'asset_id' or 'slug'"
        )

    package_id = None
    if "package_id" in payload:
        try:
            package_id = int(payload["package_id"])
        except (TypeError, ValueError):
            package_id = None

    if package_id is not None:
        for asset in candidates:
            if asset.learnpack_id is None:
                asset.learnpack_id = package_id
                asset.save()

    all_slugs: set[str] = set()
    for asset in candidates:
        all_slugs.update(translation_slugs_for_asset(asset))

    asset_tasks = Task.objects.filter(associated_slug__in=all_slugs, user__id=webhook.student.id)
    if not asset_tasks.exists():
        logger.warning(
            "learnpack batch abort no matching task student_id=%s slugs=%s",
            webhook.student.id,
            sorted(all_slugs),
        )
        raise Exception(
            f"Student with id {webhook.student.id} has not tasks with associated slug in any of the asset translations: {sorted(all_slugs)}"
        )

    group_task_counts: Counter[int] = Counter()
    group_canonical: dict[int, Asset] = {}
    for task in asset_tasks:
        asset = Asset.objects.filter(slug=task.associated_slug).first()
        if asset is None:
            continue
        canonical = asset.get_canonical_translation_asset()
        group_task_counts[canonical.id] += 1
        group_canonical[canonical.id] = canonical

    if not group_canonical:
        logger.warning(
            "learnpack batch abort tasks without registry assets student_id=%s",
            webhook.student.id,
        )
        raise Exception(
            f"Student with id {webhook.student.id} has not tasks with associated slug in any of the asset translations: {sorted(all_slugs)}"
        )

    canonical_id = max(group_canonical.keys(), key=lambda asset_id: (group_task_counts[asset_id], -asset_id))
    canonical_asset = group_canonical[canonical_id]
    canonical_slug = canonical_asset.slug
    group_slugs = translation_slugs_for_asset(canonical_asset)
    asset_tasks = asset_tasks.filter(associated_slug__in=group_slugs)

    logger.info(
        "learnpack batch matched student_id=%s canonical_asset_id=%s canonical_slug=%s task_count=%s candidate_count=%s",
        webhook.student.id,
        canonical_asset.id,
        canonical_slug,
        asset_tasks.count(),
        len(candidates),
    )

    telemetry = AssignmentTelemetry.objects.filter(asset_slug=canonical_slug, user__id=payload["user_id"]).first()

    if telemetry is None:
        telemetry = AssignmentTelemetry(user=webhook.student, asset_slug=canonical_slug, telemetry=payload)
        telemetry.save()
    else:
        telemetry.telemetry = payload
        telemetry.save()

    for task in asset_tasks:
        if task.telemetry_id != telemetry.id:
            task.telemetry = telemetry
            task.save()

    calculate_telemetry_indicator(telemetry, asset_tasks)
    logger.info(
        "learnpack batch done student_id=%s telemetry_id=%s canonical_slug=%s",
        webhook.student.id,
        telemetry.id,
        canonical_slug,
    )

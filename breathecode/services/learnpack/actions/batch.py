import logging
from datetime import timedelta
from django.utils import timezone
logger = logging.getLogger(__name__)
from breathecode.assignments.models import AssignmentTelemetry, LearnPackWebhook
from breathecode.assignments.utils.indicators import EngagementIndicator, FrustrationIndicator, UserIndicatorCalculator
from breathecode.assignments.actions import calculate_telemetry_indicator

def batch(self, webhook: LearnPackWebhook):
    # lazyload to fix circular import
    from breathecode.assignments.models import Task
    from breathecode.registry.models import Asset
    from breathecode.services.learnpack.resolve_payload_asset import resolve_asset_from_payload_asset_id

    asset = None
    if "asset_id" in webhook.payload:
        _id = webhook.payload["asset_id"]
        asset = resolve_asset_from_payload_asset_id(_id)
        if asset is not None and asset.learnpack_id is None and "package_id" in webhook.payload:
            asset.learnpack_id = int(webhook.payload["package_id"])
            asset.save()

    if asset is None:
        _slug = None
        if "slug" in webhook.payload:
            _slug = webhook.payload["slug"]
        elif "package_slug" in webhook.payload:
            _slug = webhook.payload["package_slug"]

        if _slug is not None:
            asset = Asset.get_by_slug(_slug)

    # Final fallback: try resolving by LearnPack package_id if available.
    if asset is None and "package_id" in webhook.payload:
        try:
            package_id = int(webhook.payload["package_id"])
            asset = Asset.objects.filter(learnpack_id=package_id).first()
        except (TypeError, ValueError):
            asset = None

    if asset is None:
        raise Exception(
            "Asset specified by learnpack telemetry was not found using either the payload 'asset_id' or 'slug'"
        )

    canonical_asset = asset.get_canonical_translation_asset()
    canonical_slug = canonical_asset.slug
    translation_slugs = {canonical_slug, asset.slug}
    translation_slugs.update(elem.slug for elem in canonical_asset.all_translations.all() if elem and elem.slug)

    telemetry = AssignmentTelemetry.objects.filter(
        asset_slug=canonical_slug, user__id=webhook.payload["user_id"]
    ).first()

    asset_tasks = Task.objects.filter(associated_slug__in=translation_slugs, user__id=webhook.student.id)
    if asset_tasks.count() == 0:
        raise Exception(
            f"Student with id {webhook.student.id} has not tasks with associated slug in any of the asset translations: {sorted(translation_slugs)}"
        )

    if telemetry is None:
        telemetry = AssignmentTelemetry(user=webhook.student, asset_slug=canonical_slug, telemetry=webhook.payload)
        telemetry.save()
        # All assets with the same associated slug should share the same telemetry
        for a in asset_tasks:
            a.telemetry = telemetry
            a.save()
    else:
        telemetry.telemetry = webhook.payload
        telemetry.save()

    # Calculate indicators
    calculate_telemetry_indicator(telemetry, asset_tasks)
    

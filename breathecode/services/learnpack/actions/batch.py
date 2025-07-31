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

    asset = None
    if "asset_id" in webhook.payload:
        _id = webhook.payload["asset_id"]
        asset = Asset.objects.filter(id=_id).first()

    if asset is None:
        _slug = webhook.payload["slug"]
        asset = Asset.get_by_slug(_slug)

    if asset is None:
        raise Exception(
            "Asset specified by learnpack telemetry was not found using either the payload 'asset_id' or 'slug'"
        )

    telemetry = AssignmentTelemetry.objects.filter(asset_slug=asset.slug, user__id=webhook.payload["user_id"]).first()

    asset_tasks = Task.objects.filter(associated_slug=asset.slug, user__id=webhook.student.id)
    if asset_tasks.count() == 0:
        raise Exception(f"Student with id {webhook.student.id} has not tasks with associated slug {asset.slug}")

    if telemetry is None:
        telemetry = AssignmentTelemetry(user=webhook.student, asset_slug=asset.slug, telemetry=webhook.payload)
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
    

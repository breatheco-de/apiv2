import logging
import time

logger = logging.getLogger(__name__)


def batch(self, webhook):
    # lazyload to fix circular import
    from breathecode.assignments.models import Task

    _slug = webhook.payload['slug']

    telemetry = AssignmentTelemetry.objects.filter(asset_slug=_slug,
                                                   user__id=webhook.payload['user_id']).first()

    assets = Task.objects.filter(slug=_slug, user__id=webhook.user.id)
    if assets.count() == 0:
        raise Exception(f'Student with id {webhook.user.id} has not tasks with associated slug {_slug}')

    if telemetry is None:
        telemetry = AssignmentTelemetry(user=webhook.user, asset_slug=_slug, telemetry=webhook.payload)
        telemetry.save()
        # All assets with the same associated slug should share the same telemetry
        for a in assets:
            a.telemetry = telemetry
            a.save()

    else:
        telemetry.telemetry = webhook.payload
        telemetry.save()

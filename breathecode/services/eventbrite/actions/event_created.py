import logging
import time

logger = logging.getLogger(__name__)


def event_created(self, webhook, payload: dict):
    # lazyload to fix circular import
    from breathecode.events.models import Organization
    from breathecode.events.actions import update_or_create_event

    org = Organization.objects.filter(id=webhook.organization_id).first()

    # prevent receive a event.created before save the event in the first time
    time.sleep(3)

    event = update_or_create_event(payload, org)
    if event and event is not None:
        webhook.event = event
        webhook.save()

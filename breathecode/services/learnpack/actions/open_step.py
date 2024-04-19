import logging

logger = logging.getLogger(__name__)


def open_step(self, webhook):
    # lazyload to fix circular import
    from breathecode.events.actions import publish_event_from_eventbrite
    from breathecode.events.models import Organization

    org = Organization.objects.filter(id=webhook.organization_id).first()

    # FIXME: undefined variable payload
    event = publish_event_from_eventbrite(payload, org)
    if event and event is not None:
        webhook.event = event
        webhook.save()

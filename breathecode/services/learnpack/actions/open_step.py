import logging

from breathecode.assignments.models import LearnPackWebhook

logger = logging.getLogger(__name__)


def open_step(self, webhook: LearnPackWebhook):
    # lazyload to fix circular import
    from breathecode.events.actions import publish_event_from_eventbrite
    from breathecode.events.models import Organization

    org = Organization.objects.filter(id=webhook.organization_id).first()

    event = publish_event_from_eventbrite(webhook.payload, org)
    if event and event is not None:
        webhook.event = event
        webhook.save()

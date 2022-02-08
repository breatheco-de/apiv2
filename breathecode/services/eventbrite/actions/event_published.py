import logging

logger = logging.getLogger(__name__)


def event_published(self, webhook, payload: dict):
    # lazyload to fix circular import
    from breathecode.events.models import Organization
    from breathecode.events.actions import publish_event_from_eventbrite

    org = Organization.objects.filter(id=webhook.organization_id).first()

    publish_event_from_eventbrite(payload, org)

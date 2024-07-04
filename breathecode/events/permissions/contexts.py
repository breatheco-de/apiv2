from breathecode.events.models import Event, EventType
from breathecode.services import LaunchDarkly


def event(client: LaunchDarkly, event: Event):
    key = f"{event.id}"
    name = event.title
    kind = "event"
    context = {
        "id": event.id,
        "slug": event.slug,
        "lang": event.lang,
        "academy": event.academy.slug if event.academy else "unknown",
        "organization": event.organization.name if event.organization else "unknown",
        "published_at": event.published_at,
        "event_type": event.event_type.slug if event.event_type else "unknown",
    }

    return client.context(key, name, kind, context)


def event_type(client: LaunchDarkly, event_type: EventType):
    key = f"{event_type.id}"
    name = event_type.name
    kind = "event-type"
    context = {
        "id": event_type.id,
        "slug": event_type.slug,
        "academy": event_type.academy.slug,
        "lang": event_type.lang,
    }

    return client.context(key, name, kind, context)

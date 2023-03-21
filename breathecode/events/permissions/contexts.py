from breathecode.events.models import Event, EventType
from breathecode.services import LaunchDarkly


def event(client: LaunchDarkly, event: Event):
    print('event', event)
    key = f'event-{event.id}'
    name = event.title
    kind = 'event-information'
    author = (f'{event.author.first_name} {event.author.last_name} ({event.author.email})'
              if event.author else 'unknown')
    context = {
        'id': event.id,
        'slug': event.slug,
        'title': event.title,
        'lang': event.lang,
        'capacity': event.capacity,
        'host': event.host,
        'academy': event.academy.slug if event.academy else 'unknown',
        'organization': event.organization.name if event.organization else 'unknown',
        'author': author,
        'host': event.host,
        'online_event': event.online_event,
        'status': event.status,
        'published_at': event.published_at,
        'event_type': event.event_type.slug if event.event_type else 'unknown',
    }

    return client.context(key, name, kind, context)


def event_type(client: LaunchDarkly, event_type: EventType):
    key = f'event-type-{event_type.id}'
    name = event_type.name
    kind = 'event-type-information'
    context = {
        'id': event_type.id,
        'slug': event_type.slug,
        'name': event_type.name,
        'academy': event_type.academy.slug,
        'lang': event_type.lang,
        'allow_shared_creation': event_type.allow_shared_creation,
    }

    return client.context(key, name, kind, context)

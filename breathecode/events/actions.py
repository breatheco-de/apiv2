import logging
from datetime import datetime, timedelta
from .models import Organization, Venue, Event, Organizer
from .utils import Eventbrite
from django.utils import timezone

logger = logging.getLogger(__name__)

status_map = {
    'draft': 'DRAFT',
    'live': 'ACTIVE',
    'completed': 'COMPLETED',
    'started': 'ACTIVE',
    'ended': 'ACTIVE',
    'canceled': 'DELETED',
}


def sync_org_venues(org):
    if org.academy is None:
        raise Exception('First you must specify to which academy this organization belongs')

    client = Eventbrite(org.eventbrite_key)
    result = client.get_organization_venues(org.eventbrite_id)

    for data in result['venues']:
        create_or_update_venue(data, org, force_update=True)

    return True


def create_or_update_organizer(data, org, force_update=False):
    if org.academy is None:
        raise Exception('First you must specify to which academy this organization belongs')

    organizer = Organizer.objects.filter(eventbrite_id=data['id']).first()

    try:
        if organizer is None:
            organizer = Organizer(name=data['name'],
                                  description=data['description']['text'],
                                  eventbrite_id=data['id'],
                                  organization=org)
            organizer.save()

        elif force_update == True:
            organizer.name = data['name']
            organizer.description = data['description']['text']
            organizer.save()

    except Exception as e:
        print('Error saving organizer eventbrite_id: ' + str(data['id']) + ' skipping to the next', e)

    return organizer


def create_or_update_venue(data, org, force_update=False):
    if not org.academy:
        logger.error(f'The organization {org} not have a academy assigned')
        return

    venue = Venue.objects.filter(eventbrite_id=data['id'], academy__id=org.academy.id).first()

    if venue and not force_update:
        return

    kwargs = {
        'title': data['name'],
        'street_address': data['address']['address_1'],
        'country': data['address']['country'],
        'city': data['address']['city'],
        'state': data['address']['region'],
        'zip_code': data['address']['postal_code'],
        'latitude': data['latitude'],
        'longitude': data['longitude'],
        'eventbrite_id': data['id'],
        'eventbrite_url': data['resource_uri'],
        'academy': org.academy,
        # 'organization': org,
    }

    try:
        if venue is None:
            Venue(**kwargs).save()

        elif force_update == True:
            for attr in kwargs:
                setattr(venue, attr, kwargs[attr])

            venue.save()

    except:
        logger.error(f'Error saving venue eventbrite_id: {data["id"]} skipping to the next')

    return venue


def export_event_to_eventbrite(event: Event, org: Organization):
    if not org.academy:
        logger.error(f'The organization {org} not have a academy assigned')
        return

    timezone = org.academy.timezone
    client = Eventbrite(org.eventbrite_key)
    now = get_current_iso_string()

    data = {
        'event.name.html': event.title,
        'event.description.html': event.description,
        'event.start.utc': event.starting_at.isoformat(),
        'event.end.utc': event.ending_at.isoformat(),
        'event.summary': event.excerpt,
        'event.capacity': event.capacity,
        'event.online_event': event.online_event,
        'event.url': event.eventbrite_url,
        'event.currency': event.currency,
    }

    if timezone:
        data['event.start.timezone'] = timezone
        data['event.end.timezone'] = timezone

    try:
        if event.eventbrite_id:
            client.update_organization_event(event.eventbrite_id, data)

        else:
            result = client.create_organization_event(org.eventbrite_id, data)
            event.eventbrite_id = str(result['id'])

        event.eventbrite_sync_description = now
        event.eventbrite_sync_status = 'SYNCHED'

    except Exception as e:
        event.eventbrite_sync_description = f'{now} => {e}'
        event.eventbrite_sync_status = 'ERROR'

    event.save()
    return event


def sync_org_events(org):
    if not org.academy:
        logger.error(f'The organization {org} not have a academy assigned')
        return

    client = Eventbrite(org.eventbrite_key)
    result = client.get_organization_events(org.eventbrite_id)

    try:
        for data in result['events']:
            update_or_create_event(data, org)

        org.sync_status = 'PERSISTED'
        org.sync_desc = f"Success with {len(result['events'])} events..."
        org.save()

    except Exception as e:
        if org:
            org.sync_status = 'ERROR'
            org.sync_desc = 'Error: ' + str(e)
            org.save()
        raise e

    events = Event.objects.filter(sync_with_eventbrite=True, eventbrite_sync_status='PENDING')
    for event in events:
        export_event_to_eventbrite(event, org)

    return True


# use for mocking purpose
def get_current_iso_string():
    return str(timezone.now())


def update_or_create_event(data, org):
    if data is None:  #skip if no data
        logger.warn('Ignored event')
        return False

    if not org.academy:
        logger.error(f'The organization {org} not have a academy assigned')
        return

    now = get_current_iso_string()

    if data['status'] not in status_map:
        raise Exception('Uknown eventbrite status ' + data['status'])

    event = Event.objects.filter(eventbrite_id=data['id'], organization__id=org.id).first()
    try:
        venue = None
        if 'venue' in data:
            venue = create_or_update_venue(data['venue'], org)
        organizer = None
        if 'organizer' in data:
            organizer = create_or_update_organizer(data['organizer'], org, force_update=True)
        else:
            print('Event without organizer', data)

        kwargs = {
            'title': data['name']['text'],
            'description': data['description']['text'],
            'excerpt': data['description']['text'],
            'starting_at': data['start']['utc'],
            'ending_at': data['end']['utc'],
            'capacity': data['capacity'],
            'online_event': data['online_event'],
            'eventbrite_id': data['id'],
            'eventbrite_url': data['url'],
            'status': status_map[data['status']],
            'eventbrite_status': data['status'],
            'currency': data['currency'],
            'organization': org,
            # organizer: organizer,
            'venue': venue,
        }

        if event is None:
            event = Event(**kwargs)

        else:
            for attr in kwargs:
                setattr(event, attr, kwargs[attr])

        if 'published' in data:
            event.published_at = data['published']

        if 'logo' in data and data['logo'] is not None:
            event.banner = data['logo']['url']

        if not event.url:
            event.url = event.eventbrite_url

        # look for the academy ownership based on organizer first
        if organizer is not None and organizer.academy is not None:
            event.academy = organizer.academy

        elif org.academy is not None:
            event.academy = org.academy

        event.save()

        event.eventbrite_sync_description = now
        event.eventbrite_sync_status = 'PERSISTED'
        event.save()

    except Exception as e:
        if event is not None:
            event.eventbrite_sync_description = f'{now} => {e}'
            event.eventbrite_sync_status = 'ERROR'
            event.save()
        raise e

    return event


def fix_datetime_weekday(current, timeslot, prev=False, next=False):
    if not prev and not next:
        raise Exception('You should provide a prev or next argument')

    days = 0
    weekday = timeslot.weekday()
    postulate = datetime(year=current.year,
                         month=current.month,
                         day=current.day,
                         hour=timeslot.hour,
                         minute=timeslot.minute,
                         second=timeslot.second,
                         tzinfo=current.tzinfo)

    while True:
        if prev:
            res = postulate - timedelta(days=days)
            if weekday == res.weekday():
                return res

        if next:
            res = postulate + timedelta(days=days)
            if weekday == res.weekday():
                return res

        days = days + 1

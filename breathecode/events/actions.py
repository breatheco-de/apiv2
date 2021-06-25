from datetime import datetime, timedelta
from breathecode.admissions.models import CohortTimeSlot
from .models import Organization, Venue, Event, Organizer
from .utils import Eventbrite
from django.utils import timezone

status_map = {
    "draft": 'DRAFT',
    "live": 'ACTIVE',
    "completed": 'COMPLETED',
    "started": 'ACTIVE',
    "ended": 'ACTIVE',
    "canceled": 'DELETED',
}


def sync_org_venues(org):

    if org.academy is None:
        raise Exception(
            'First you must specify to which academy this organization belongs'
        )
    # client.get_my_organizations()
    # self.stdout.write(self.style.SUCCESS("Successfully sync organizations"))
    client = Eventbrite(org.eventbrite_key)
    result = client.get_organization_venues(org.eventbrite_id)
    for data in result['venues']:
        create_or_update_venue(data, org, force_update=True)

    return True


def create_or_update_organizer(data, org, force_update=False):
    organizer = Organizer.objects.filter(eventbrite_id=data['id']).first()

    try:
        if organizer is None:
            organizer = Organizer(name=data['name'],
                                  description=data['description']['text'],
                                  eventbrite_id=data['id'],
                                  organization=org)
            organizer.save()
        elif force_update == True:
            organizer.title = data['name']
            organizer.description = data['description']['text']
            organizer.save()
    except Exception as e:
        print(
            "Error saving organizer eventbrite_id: " + str(data['id']) +
            " skipping to the next", e)

    return organizer


def create_or_update_venue(data, org, force_update=False):
    venue = Venue.objects.filter(eventbrite_id=data['id'],
                                 academy__id=org.academy.id).first()

    try:
        if venue is None:
            venue = Venue(
                title=data['name'],
                street_address=data['address']['address_1'],
                country=data['address']['country'],
                city=data['address']['city'],
                state=data['address']['region'],
                zip_code=data['address']['postal_code'],
                latitude=data['latitude'],
                longitude=data['longitude'],
                eventbrite_id=data['id'],
                eventbrite_url=data['resource_uri'],
                academy=org.academy,
            )
            venue.save()
        elif force_update == True:
            venue.title = data['name']
            venue.street_address = data['address']['address_1']
            venue.country = data['address']['country']
            venue.city = data['address']['city']
            venue.state = data['address']['region'],
            venue.zip_code = data['address']['postal_code']
            venue.latitude = data['latitude']
            venue.longitude = data['longitude']
            venue.eventbrite_url = data['resource_uri']
            venue.save()
    except:
        print("Error saving venue eventbrite_id: " + str(data['id']) +
              " skipping to the next")

    return venue


def sync_org_events(org):

    client = Eventbrite(org.eventbrite_key)
    result = client.get_organization_events(org.eventbrite_id)

    try:
        for data in result['events']:
            update_or_create_event(data, org)

        org.sync_status = 'PERSISTED'
        org.sync_desc = f"Success with {len(result['events'])} events..."
        org.save()
    except Exception as e:
        if org is not None:
            org.sync_status = 'ERROR'
            org.sync_desc = "Error: " + str(e)
            org.save()
        raise e

    return True


def update_or_create_event(data, org):

    if data is None:  #skip if no data
        print("Ignored event")
        return False

    now = timezone.now()

    if data['status'] not in status_map:
        raise Exception("Uknown eventbrite status " + data['status'])

    event = Event.objects.filter(eventbrite_id=data['id'],
                                 organization__id=org.id).first()
    try:
        venue = None
        if 'venue' in data:
            venue = create_or_update_venue(data['venue']['id'], org)
        organizer = None
        if 'organizer' in data:
            organizer = create_or_update_organizer(data['organizer'],
                                                   org,
                                                   force_update=True)
        else:
            print("Event without organizer", data)

        if event is None:
            event = Event(
                title=data['name']['text'],
                description=data['description']['text'],
                excerpt=data['description']['text'],
                starting_at=data['start']['utc'],
                ending_at=data['end']['utc'],
                capacity=data['capacity'],
                online_event=data['online_event'],
                eventbrite_id=data['id'],
                eventbrite_url=data['url'],
                status=status_map[data['status']],
                eventbrite_status=data['status'],
                organization=org,
                # organizer=organizer,
                venue=venue,
            )
        else:
            event.title = data['name']['text']
            event.description = data['description']['text']
            event.excerpt = data['description']['text']
            event.starting_at = data['start']['utc']
            event.ending_at = data['end']['utc']
            event.capacity = data['capacity']
            event.online_event = data['online_event']
            event.eventbrite_id = data['id']
            event.eventbrite_url = data['url']
            event.status = status_map[data['status']]
            event.eventbrite_status = data['status']
            # event.organizer=organizer
            event.venue = venue

        if "published" in data:
            event.published_at = data['published']
        if "logo" in data and data['logo'] is not None:
            event.banner = data['logo']['url']
        if event.url is None or event.url == "":
            event.url = event.eventbrite_url

        # look for the academy ownership based on organizer first
        if organizer is not None and organizer.academy is not None:
            event.academy = organizer.academy
        elif Organization.academy is not None:
            event.academy = organizer.academy

        event.save()

        event.sync_desc = str(now)
        event.sync_status = 'PERSISTED'
        event.save()
    except Exception as e:
        if event is not None:
            event.sync_desc = str(now) + " => " + str(e)
            event.sync_status = 'ERROR'
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

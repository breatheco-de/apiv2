import os, requests
from rest_framework.exceptions import ValidationError
from .models import Organizacion, Venue, Event
from .utils import Eventbrite

def sync_org_venues(org):

    if org.academy is None:
        raise Exception('First you must specify to which academy this organization belongs')
    # client.get_my_organizations()
    # self.stdout.write(self.style.SUCCESS("Successfully sync organizations"))
    client = Eventbrite(org.eventbrite_key)
    result = client.get_organization_venues(org.eventbrite_id)
    for data in result['venues']:
        venue = Venue.objects.filter(eventbrite_id=data['id'], academy__id=org.academy.id).first()
        try:
            if venue is not None:
                venue.title=data['name']
                venue.street_address=data['address']['address_1']
                venue.country=data['address']['country']
                venue.city=data['address']['city']
                venue.state=data['address']['region'],
                venue.zip_code=data['address']['postal_code']
                venue.latitude=data['latitude']
                venue.longitude=data['longitude']
                venue.eventbrite_url=data['resource_uri']
            else:
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
        except:
            print("Error saving venue eventbrite_id: "+str(data['id'])+" skipping to the next")
        venue.save()

    return True

def sync_org_events(org):

    client = Eventbrite(org.eventbrite_key)
    result = client.get_organization_events(org.eventbrite_id)
        
    for data in result['events']:
        event = Event(
            title=data['title']['text'],
            description=data['description']['text'],
            starting_at=data['start']['utc'],
            ending_at=data['end']['utc'],
            capacity=data['capacity'],
            status=data['status'],
        )

    return True
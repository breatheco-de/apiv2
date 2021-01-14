from django.contrib.auth.models import User

def placed(self, payload: dict):
    # prevent circular dependency import between thousand modules previuosly loaded and cached
    from breathecode.marketing.actions import add_to_active_campaign
    from breathecode.events.models import EventCheckin, Event

    event = payload['event']
    attendees = payload['attendees']
    attendee_profile = attendees[0]['profile']

    local_event = Event.objects.filter(eventbrite_id=event['id']).first()

    if not local_event:
        raise Exception('event doesn\'t exist')

    local_attendee = User.objects.filter(email=attendee_profile['email']).first()

    # prevent one event_checkin with same event and email
    event_checkin = EventCheckin(
        email=payload['email'],
        status='PENDING',
        event=local_event,
        attendee=local_attendee).save()

    # TODO: local_event.academy
    contact = {
        'email': payload['email'],
        'first_name': payload['first_name'],
        'last_name': payload['last_name'],
    }

    # TODO: if active campaign academy . event attendee automation != null then 37
    # if active_campaign_academy.event_attendancy_automation
    # if ActiveCampaignAcademy.objects.filter(academy__slug=academy_slug)
    add_to_active_campaign(contact)

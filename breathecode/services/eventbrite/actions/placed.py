from django.contrib.auth.models import User

def placed(self, payload: dict):
    # prevent circular dependency import between thousand modules previuosly loaded and cached
    from breathecode.marketing.actions import add_to_active_campaign
    from breathecode.events.models import EventCheckin, Event

    # wonderful way to fix one poor mocking system
    import requests

    if not 'email' in payload:
        pass

    from pprint import pprint
    # print('adssadasdsadsad', payload)
    pprint(payload.keys())

    # event_id = payload['event_id']
    event = payload['event']
    attendees = payload['attendees']
    attendee_profile = attendees[0]['profile']

    # print([key for key in event.keys() if hasattr(ee, key)])
    local_event = Event.objects.filter(eventbrite_id=event['id']).first()

    if not local_event:
        raise Exception('event not exist previously')

    local_attendee = User.objects.filter(
        email=attendee_profile['email'],
        first_name=attendee_profile['first_name'],
        last_name=attendee_profile['last_name']).first()

    if not local_attendee:
        raise Exception('attendee not exist previously')

    EventCheckin(
        email=payload['email'],
        status='PENDING',
        event=local_event,
        attendee=local_attendee).save()

    contact = {
        'email': payload['email'],
        'first_name': payload['first_name'],
        'last_name': payload['last_name'],
        # 'name': payload['name'],
    }

    print(payload.keys())
    print(contact)

    add_to_active_campaign(contact)

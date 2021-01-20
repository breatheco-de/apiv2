import logging
from django.contrib.auth.models import User


logger = logging.getLogger(__name__)


def order_placed(self, webhook, payload: dict):
    # prevent circular dependency import between thousand modules previuosly loaded and cached
    from breathecode.marketing.actions import add_to_active_campaign
    from breathecode.events.models import EventCheckin, Event
    from breathecode.events.models import Organization
    from breathecode.marketing.models import ActiveCampaignAcademy

    academy_id = Organization.objects.filter(id=webhook.organization_id).values_list('academy__id',
        flat=True).first()

    if not academy_id:
        message = 'Cannot get academy_id or organization doesn\'t exist'
        logger.debug(message)
        raise Exception(message)

    print(payload)

    event_id = payload['event_id']
    # attendees = payload['attendees']
    # attendee_profile = attendees[0]['profile']

    local_event = Event.objects.filter(eventbrite_id=event_id).first()

    if not local_event:
        message = 'event doesn\'t exist'
        logger.debug(message)
        raise Exception(message)

    # local_attendee = User.objects.filter(email=attendee_profile['email']).first()
    local_attendee = None

    if not EventCheckin.objects.filter(email=payload['email'], event=local_event).count():
        EventCheckin(email=payload['email'], status='PENDING', event=local_event,
            attendee=local_attendee).save()

    contact = {
        'email': payload['email'],
        'first_name': payload['first_name'],
        'last_name': payload['last_name'],
        'academy': academy_id,
    }

    if not ActiveCampaignAcademy.objects.filter(academy_id=academy_id).count():
        message = 'ActiveCampaignAcademy doesn\'t exist'
        logger.debug(message)
        raise Exception(message)
    
    automation_id = ActiveCampaignAcademy.objects.filter(academy_id=academy_id).values_list(
        'event_attendancy_automation__id', flat=True).first()

    if automation_id:
        add_to_active_campaign(contact, academy_id, automation_id)
    else:
        message = 'Automation doesn\'t exist'
        logger.debug(message)
        raise Exception(message)

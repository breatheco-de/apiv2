import logging
from django.contrib.auth.models import User


logger = logging.getLogger(__name__)


def order_placed(self, webhook, payload: dict):
    # prevent circular dependency import between thousand modules previuosly loaded and cached
    from breathecode.marketing.actions import add_to_active_campaign
    from breathecode.events.models import EventCheckin, Event
    from breathecode.events.models import Organization
    from breathecode.marketing.models import ActiveCampaignAcademy

    org = Organization.objects.filter(id=webhook.organization_id).first()

    if org is None:
        message = 'Organization doesn\'t exist'
        logger.debug(message)
        raise Exception(message)

    academy_id = org.academy.id
    event_id = payload['event_id']

    local_event = Event.objects.filter(eventbrite_id=event_id).first()

    if not local_event:
        message = 'event doesn\'t exist'
        logger.debug(message)
        raise Exception(message)

    local_attendee = User.objects.filter(email=payload['email']).first()

    if not EventCheckin.objects.filter(email=payload['email'],
            event=local_event).count():
        EventCheckin(email=payload['email'], status='PENDING', event=local_event,
            attendee=local_attendee).save()

    elif not EventCheckin.objects.filter(email=payload['email'],
            event=local_event, attendee=local_attendee).count():
        event_checkin = EventCheckin.objects.filter(email=payload['email'],
            event=local_event).first()
        event_checkin.attendee = local_attendee
        event_checkin.save()

    contact = {
        'email': payload['email'],
        'first_name': payload['first_name'],
        'last_name': payload['last_name'],
        'academy': org.academy.slug,
    }

    if not ActiveCampaignAcademy.objects.filter(academy__id=academy_id).count():
        message = 'ActiveCampaignAcademy doesn\'t exist'
        logger.debug(message)
        raise Exception(message)
    
    automation_id = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).values_list(
        'event_attendancy_automation__id', flat=True).first()

    if automation_id:
        add_to_active_campaign(contact, academy_id, automation_id)
    else:
        message = f'Automation for order_placed doesn\'t exist'
        logger.debug(message)
        raise Exception(message)

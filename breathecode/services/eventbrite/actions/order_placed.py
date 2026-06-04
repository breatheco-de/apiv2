import logging

logger = logging.getLogger(__name__)
SOURCE = "eventbrite"
CAMPAIGN = "eventbrite order placed"


def order_placed(self, webhook, payload: dict):
    from breathecode.events.actions import register_event_attendee_from_external
    from breathecode.events.models import Event, Organization

    org = Organization.objects.filter(id=webhook.organization_id).first()

    if org is None:
        message = "Organization doesn't exist"
        logger.debug(message)
        raise Exception(message)

    if not org.academy:
        raise Exception("Organization not have one Academy")

    event_id = payload["event_id"]
    email = payload["email"]

    local_event = Event.objects.filter(eventbrite_id=event_id).first()

    if not local_event or local_event is None:
        message = "event doesn't exist"
        logger.debug(message)
        raise Exception(message)
    webhook.event = local_event

    _, attendee = register_event_attendee_from_external(
        event=local_event,
        email=email,
        first_name=payload["first_name"],
        last_name=payload["last_name"],
        utm_source=SOURCE,
        campaign=CAMPAIGN,
        organization=org,
    )

    if attendee is not None:
        webhook.attendee = attendee

    webhook.save()

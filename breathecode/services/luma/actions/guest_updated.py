import logging
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

SOURCE = "luma"
CAMPAIGN = "luma guest registered"


def _get_checked_in_at(data: dict):
    checked_in_at = data.get("checked_in_at")
    if checked_in_at:
        return checked_in_at

    for ticket in data.get("event_tickets") or []:
        if isinstance(ticket, dict) and ticket.get("checked_in_at"):
            return ticket.get("checked_in_at")

    return None


def guest_updated(self, webhook, payload: dict, organization):
    from breathecode.events.actions import register_event_attendee_from_external
    from breathecode.events.models import Event, EventCheckin

    if organization.academy is None:
        raise Exception("Organization not have one Academy")

    data = payload.get("data") or {}
    event_data = data.get("event") or {}
    luma_event_id = event_data.get("id")
    if not luma_event_id:
        raise Exception("Missing Luma event id in payload")

    if organization.luma_calendar_id:
        calendar_id = event_data.get("calendar_id")
        if calendar_id and calendar_id != organization.luma_calendar_id:
            raise Exception("Webhook calendar_id does not match organization luma_calendar_id")

    local_event = Event.objects.filter(luma_id=luma_event_id).first()
    if local_event is None:
        raise Exception("event doesn't exist")

    webhook.event = local_event
    email = data.get("user_email")
    luma_guest_id = data.get("id")

    checkin = None
    if luma_guest_id:
        checkin = EventCheckin.objects.filter(event=local_event, luma_guest_id=luma_guest_id).first()

    if checkin is None and email:
        checkin = EventCheckin.objects.filter(event=local_event, email=email).first()

    approval_status = data.get("approval_status")
    if checkin is None and approval_status == "approved" and email:
        first_name = data.get("user_first_name") or ""
        last_name = data.get("user_last_name") or ""
        if not first_name and not last_name and data.get("user_name"):
            name_parts = str(data.get("user_name")).strip().split()
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        checkin, attendee = register_event_attendee_from_external(
            event=local_event,
            email=email,
            first_name=first_name,
            last_name=last_name,
            utm_source=SOURCE,
            campaign=CAMPAIGN,
            organization=organization,
        )
        if luma_guest_id:
            checkin.luma_guest_id = luma_guest_id
            checkin.save(update_fields=["luma_guest_id", "updated_at"])
        if attendee is not None:
            webhook.attendee = attendee

    if checkin is None:
        raise Exception("EventCheckin doesn't exist")

    checked_in_at = _get_checked_in_at(data)
    if checked_in_at:
        attended_at = parse_datetime(checked_in_at) if isinstance(checked_in_at, str) else checked_in_at
        checkin.status = "DONE"
        checkin.attended_at = attended_at
        checkin.save()

    if checkin.attendee is not None:
        webhook.attendee = checkin.attendee

    webhook.save()

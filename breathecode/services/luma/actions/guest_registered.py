import logging

logger = logging.getLogger(__name__)

SOURCE = "luma"
CAMPAIGN = "luma guest registered"


def guest_registered(self, webhook, payload: dict, organization):
    from breathecode.events.actions import register_event_attendee_from_external
    from breathecode.events.models import Event

    if organization.academy is None:
        raise Exception("Organization not have one Academy")

    data = payload.get("data") or {}
    approval_status = data.get("approval_status")
    if approval_status != "approved":
        webhook.status = "DONE"
        webhook.status_text = f"skipped: approval_status={approval_status}"
        webhook.save()
        return

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
    if not email:
        raise Exception("Missing guest email in payload")

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

    if data.get("id"):
        checkin.luma_guest_id = data.get("id")
        checkin.save(update_fields=["luma_guest_id", "updated_at"])

    if attendee is not None:
        webhook.attendee = attendee

    webhook.save()

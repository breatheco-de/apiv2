from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from breathecode.utils.decorators import issue, supervisor

from .actions import ensure_calendar_event_for_event, invite_emails_to_event_calendar
from .models import Event, EventCheckin
from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.services.google_calendar.google_calendar import GoogleCalendar


logger = logging.getLogger(__name__)


@supervisor(delta=timedelta(minutes=15))
def supervise_event_calendar_attendees():
    """
    Detect events with a Calendar event that are missing attendees compared
    to the EventCheckin records, and yield issues to sync them.

    Strategy:
    - Only consider ACTIVE events starting within [-1 day, +14 days] window to keep load low.
    - Skip events without academy owner credentials.
    - Ensure calendar event exists (creates it if missing) and compare attendees.
    """
    now = timezone.now()
    start = now - timedelta(days=1)
    end = now + timedelta(days=14)

    qs = Event.objects.filter(
        status="ACTIVE",
        starting_at__gte=start,
        starting_at__lte=end,
        academy__isnull=False,
    ).exclude(calendar_event_id__isnull=True)

    for event in qs.iterator():
        settings = AcademyAuthSettings.objects.filter(academy=event.academy, google_cloud_owner__isnull=False).first()
        if not settings or not hasattr(settings.google_cloud_owner, "credentialsgoogle"):
            continue

        try:
            owner_creds = settings.google_cloud_owner.credentialsgoogle
            gc = GoogleCalendar(token=owner_creds.token, refresh_token=owner_creds.refresh_token)

            calendar_event_id = ensure_calendar_event_for_event(event)

            calendar_event = gc.get_event("primary", calendar_event_id)
            current = {a.get("email").lower() for a in (calendar_event.get("attendees", []) or []) if a.get("email")}

            desired = set(
                email.lower()
                for email in EventCheckin.objects.filter(event=event).values_list("email", flat=True)
                if email
            )

            missing = sorted(list(desired - current))
            if missing:
                yield (
                    f"Event {event.id} missing {len(missing)} attendees in Google Calendar",
                    "sync-event-calendar-attendees",
                    {"event_id": event.id, "emails": missing},
                )
        except Exception as e:
            logger.warning(f"supervise_event_calendar_attendees failed for event {event.id}: {e}")


@issue(supervise_event_calendar_attendees, delta=timedelta(minutes=20), attempts=3)
def sync_event_calendar_attendees(event_id: int, emails: list[str]):
    """
    Ensure the provided emails are invited to the Google Calendar event linked
    to the Event. Returns True when fixed, False when unfixable, or None to retry.
    """
    event = Event.objects.filter(id=event_id).first()
    if not event or not event.academy:
        return True

    if not emails:
        return True

    settings = AcademyAuthSettings.objects.filter(academy=event.academy, google_cloud_owner__isnull=False).first()
    if not settings or not hasattr(settings.google_cloud_owner, "credentialsgoogle"):
        return False

    try:
        ensure_calendar_event_for_event(event)
        invite_emails_to_event_calendar(event, emails)
        return True
    except Exception as e:
        logger.warning(f"sync_event_calendar_attendees failed for event {event_id}: {e}")
        return None

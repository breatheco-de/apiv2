#!/usr/bin/env python
"""
Looks for events published without tags
"""

# flake8: noqa: F821

from breathecode.events.models import Event
from breathecode.utils import ScriptNotification
from django.utils import timezone
from breathecode.utils.datetime_integer import from_now

published_without_tags = Event.objects.filter(
    status="ACTIVE", academy__id=academy.id, tags="", ending_at__gt=timezone.now()
)
total = published_without_tags.count()

if total > 0:
    msg = ""
    for event in published_without_tags:
        msg += f'- <a href="{ADMIN_URL}/events/event/{event.id}?location={academy.slug}">{event.title}</a> added {from_now(event.created_at)} ago. \n'  # noqa: F821

    raise ScriptNotification(
        f"There are {total} published events without tags \n\n" + msg,
        status="CRITICAL",
        title=f"There are {total} events published without tags at {academy.name}",
        slug="events-without-tags",
        btn_url=ADMIN_URL + "/events/list?location=" + academy.slug,
    )

print(f"There are no events without tags for {academy.slug}")

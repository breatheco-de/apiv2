#!/usr/bin/env python
"""
There are draft events that need to be publised or deleted
"""
import os
from breathecode.events.models import Event
from breathecode.utils import ScriptNotification
from breathecode.utils.datetime_interger import duration_to_str, from_now

ADMIN_URL = os.getenv('ADMIN_URL', '')
pendings = Event.objects.filter(status='DRAFT', academy__id=academy.id)
total_pendings = pendings.count()

if total_pendings > 0:
    msg = ''
    for event in pendings:
        msg += f'- <a href="{ADMIN_URL}/events/event/{event.id}?location={academy.slug}">{event.title}</a> added {from_now(event.created_at)} ago. \n'

    raise ScriptNotification(
        f'There are {total_pendings} pending event to published or deleted \n\n' + msg,
        status='CRITICAL',
        title=f'There are {total_pendings} draft events to published or deleted in {academy.name}',
        slug='draft-events',
        btn_url=ADMIN_URL + '/events/list?location=' + academy.slug)

print(f'There are no draft events for {academy.slug}')

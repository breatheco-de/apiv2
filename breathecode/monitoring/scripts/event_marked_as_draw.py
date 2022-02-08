#!/usr/bin/env python
"""
Alert when there are Form Entries with status = PENDING
"""
from breathecode.events.models import Event
from breathecode.utils import ScriptNotification

pendings = Event.objects.filter(status='DRAFT').count()

if pendings:
    raise ScriptNotification(f'There are {pendings} pending event to published', slug='pending-events')

print('done')

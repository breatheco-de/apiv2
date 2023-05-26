"""
For each signal you want other apps to be able to receive, you have to
declare a new variable here like this:
"""
from django.dispatch import Signal

event_saved = Signal()
event_status_updated = Signal()
new_event_attendee = Signal()
new_event_order = Signal()

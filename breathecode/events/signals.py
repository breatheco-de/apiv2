"""For each signal you want other apps to be able to receive, you have to declare a new variable here like this."""

from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.events")

event_saved = emisor.signal("event_saved")
event_status_updated = emisor.signal("event_status_updated")
new_event_attendee = emisor.signal("new_event_attendee")
new_event_order = emisor.signal("new_event_order")

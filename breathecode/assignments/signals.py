"""For each signal you want other apps to be able to receive, you have to declare a new variable here like this:"""

from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.assignments")

assignment_created = emisor.signal("assignment_created")
assignment_status_updated = emisor.signal("assignment_status_updated")
revision_status_updated = emisor.signal("revision_status_updated")

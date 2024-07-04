"""For each signal you want other apps to be able to receive, you have to declare a new variable here like this."""

from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.commons")

update_cache = emisor.signal("update_cache")

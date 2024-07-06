"""For each signal you want other apps to be able to receive, you have to declare a new variable here like this:"""

from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.assessment")

assessment_updated = emisor.signal("assessment_updated")
userassessment_status_updated = emisor.signal("userassessment_status_updated")

"""For each signal you want other apps to be able to receive, you have to declare a new variable here like this:"""

from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.feedback")

# when a student answers one particular questions of a survey
survey_answered = emisor.signal("survey_answered")

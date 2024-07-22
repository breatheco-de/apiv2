"""For each signal you want other apps to be able to receive, you have to declare a new variable here like this:"""

from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.mentorship")

mentorship_session_status = emisor.signal("mentorship_session_status")
mentor_profile_saved = emisor.signal("mentor_profile_saved")
mentorship_session_saved = emisor.signal("mentorship_session_saved")

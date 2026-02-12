"""For each signal you want other apps to be able to receive, you have to declare a new variable here like this:"""

from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.monitoring")

github_webhook = emisor.signal("github_webhook")
stripe_webhook = emisor.signal("stripe_webhook")
application_created = emisor.signal("application_created")

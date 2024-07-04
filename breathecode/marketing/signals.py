"""For each signal you want other apps to be able to receive, you have to declare a new variable here like this."""

from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.marketing")

downloadable_saved = emisor.signal("downloadable_saved")

form_entry_won_or_lost = emisor.signal("form_entry_won_or_lost")
new_form_entry_deal = emisor.signal("new_form_entry_deal")

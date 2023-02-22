"""
For each signal you want other apps to be able to receive, you have to
declare a new variable here like this:
"""
from django.dispatch import Signal

invite_accepted = Signal(providing_args=['task_id'])

downloadable_saved = Signal()

form_entry_won_or_lost = Signal()

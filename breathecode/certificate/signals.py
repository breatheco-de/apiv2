"""
For each signal you want other apps to be able to receive, you have to
declare a new variable here like this:
"""
from django.dispatch import Signal

user_specialty_saved = Signal()

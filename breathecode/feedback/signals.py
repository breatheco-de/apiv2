"""
For each signal you want other apps to be able to receive, you have to
declare a new variable here like this:
"""

from django import dispatch

# when a student answers one particular questions of a survey
survey_answered = dispatch.Signal()

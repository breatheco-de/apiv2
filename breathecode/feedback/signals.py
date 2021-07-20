from django import dispatch

"""

For each signal you want other apps to be able to receive, you have to
declare a new variable here like this:

invite_accepted = dispatch.Signal(providing_args=["task_id"])
"""

survey_answered = dispatch.Signal(providing_args=["answer"])
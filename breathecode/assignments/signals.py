"""
For each signal you want other apps to be able to receive, you have to
declare a new variable here like this:
"""

from django import dispatch

assignment_created = dispatch.Signal()
assignment_status_updated = dispatch.Signal()
revision_status_updated = dispatch.Signal()

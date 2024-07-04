"""
For each signal you want other apps to be able to receive, you have to
declare a new variable here like this:
"""

from django import dispatch

github_webhook = dispatch.Signal()
stripe_webhook = dispatch.Signal()

from django import dispatch
# When a new breathecode invite has been accepted
invite_accepted = dispatch.Signal()

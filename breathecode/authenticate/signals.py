from django import dispatch

invite_accepted = dispatch.Signal(providing_args=['task_id'])

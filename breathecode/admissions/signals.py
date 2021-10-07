from django import dispatch
# When a new breathecode invite has been accepted
student_graduated = dispatch.Signal(providing_args=['task_id'])
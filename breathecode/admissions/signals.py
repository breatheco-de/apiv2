from django import dispatch

student_edu_status_updated = dispatch.Signal(providing_args=['task_id'])

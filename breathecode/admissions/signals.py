from django.dispatch import Signal

# add your receives here
student_edu_status_updated = Signal(providing_args=['task_id'])
cohort_saved = Signal()

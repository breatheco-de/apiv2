from django.dispatch import Signal

# add your receives here
student_edu_status_updated = Signal()
cohort_saved = Signal()
academy_saved = Signal()

academy_saved = Signal()

# happens when any asset gets update inside the syllabus json for any version
syllabus_asset_slug_updated = Signal()

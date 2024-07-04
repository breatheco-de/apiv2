from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.admissions")

# add your receives here
student_edu_status_updated = emisor.signal("student_edu_status_updated")
cohort_saved = emisor.signal("cohort_saved")
cohort_log_saved = emisor.signal("cohort_log_saved")
cohort_user_created = emisor.signal("cohort_user_created")
cohort_stage_updated = emisor.signal("cohort_stage_updated")

academy_saved = emisor.signal("academy_saved")

# happens when any asset gets update inside the syllabus json for any version
syllabus_asset_slug_updated = emisor.signal("syllabus_asset_slug_updated")

syllabus_version_json_updated = emisor.signal("syllabus_version_json_updated")

timeslot_saved = emisor.signal("timeslot_saved")

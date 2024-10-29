from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.authenticate")

# UserInvite accepted
invite_status_updated = emisor.signal("invite_status_updated")
# ProfileAcademy accepted
academy_invite_accepted = emisor.signal("academy_invite_accepted")
profile_academy_saved = emisor.signal("profile_academy_saved")

# post_delete and post_save for User, ProfileAcademy and MentorProfileMentorProfile
user_info_updated = emisor.signal("user_info_updated")
user_info_deleted = emisor.signal("user_info_deleted")

cohort_user_deleted = emisor.signal("cohort_user_deleted")
google_webhook_saved = emisor.signal("google_webhook_saved")

from django import dispatch

# UserInvite accepted
invite_status_updated = dispatch.Signal()
# ProfileAcademy accepted
academy_invite_accepted = dispatch.Signal()
profile_academy_saved = dispatch.Signal()

# post_delete and post_save for User, ProfileAcademy and MentorProfileMentorProfile
user_info_updated = dispatch.Signal()
user_info_deleted = dispatch.Signal()

app_scope_updated = dispatch.Signal()
cohort_user_deleted = dispatch.Signal()

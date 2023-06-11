from django import dispatch

# UserInvite accepted
invite_status_updated = dispatch.Signal()
# ProfileAcademy accepted
academy_invite_accepted = dispatch.Signal()
profile_academy_saved = dispatch.Signal()

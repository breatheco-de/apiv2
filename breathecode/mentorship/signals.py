from django import dispatch

mentorship_session_status = dispatch.Signal(providing_args=['session_id'])

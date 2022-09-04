from django.urls import path
from .views import forward_booking_url, forward_meet_url, end_mentoring_session, pick_mentorship_service

app_name = 'mentorship'
urlpatterns = [
    path('<slug:mentor_slug>', forward_booking_url, name='slug'),
    path('meet/<slug:mentor_slug>', pick_mentorship_service, name='meet_slug'),
    path('meet/<slug:mentor_slug>/service/<slug:service_slug>',
         forward_meet_url,
         name='meet_slug_service_slug'),
    path('session/<int:session_id>', end_mentoring_session, name='session_id'),
]

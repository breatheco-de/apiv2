from django.contrib import admin
from django.urls import path, include
from .views import forward_booking_url, forward_meet_url, end_mentoring_session

app_name = 'mentorship'
urlpatterns = [
    path('<slug:mentor_slug>', forward_booking_url),
    path('meet/<slug:mentor_slug>', forward_meet_url, name='meet_slug'),
    path('session/<int:session_id>', end_mentoring_session, name='close_session'),
]

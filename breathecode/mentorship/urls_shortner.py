from django.contrib import admin
from django.urls import path, include
from .views import forward_booking_url, forward_meet_url, close_mentoring_session_form

app_name = 'mentorship'
urlpatterns = [
    path('<slug:mentor_slug>', forward_booking_url),
    path('meet/<slug:mentor_slug>', forward_meet_url, name='meet_slug'),
    path('close/<int:session_id>', close_mentoring_session_form, name='close_session'),
]

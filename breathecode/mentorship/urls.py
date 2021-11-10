from django.contrib import admin
from django.urls import path, include
from .views import (ServiceView, MentorView, SessionView)

app_name = 'mentorship'
urlpatterns = [
    path('academy/service', ServiceView.as_view(), name='service'),
    path('academy/mentor', MentorView.as_view(), name='mentor'),
    path('academy/session', SessionView.as_view(), name='session'),
    path('academy/service/<int:service_id>', ServiceView.as_view(), name='service_id'),
    path('academy/mentor/<int:mentor_id>', MentorView.as_view(), name='mentor_id'),
    path('academy/session/<int:session_id>', SessionView.as_view(), name='session_id'),
]

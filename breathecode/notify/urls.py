from django.contrib import admin
from django.urls import path, include
from .views import test_email, preview_template, process_interaction, get_student_info

app_name='notify'
urlpatterns = [
    path('preview/<slug>', preview_template),
    path('test/email/<email>', test_email),
    
    path('slack/interaction', process_interaction),
    path('slack/command', get_student_info),
]


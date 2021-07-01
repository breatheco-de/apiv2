from django.contrib import admin
from django.urls import path, include
from .views import (
    test_email,
    preview_template,
    process_interaction,
    slack_command,
    preview_slack_template,
)

app_name = 'notify'
urlpatterns = [
    path('preview/<slug>', preview_template),
    path('preview/slack/<slug>', preview_slack_template),
    path('test/email/<email>', test_email),
    path('slack/interaction', process_interaction),
    path('slack/command', slack_command),
]

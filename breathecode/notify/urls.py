from django.urls import path
from .views import (
    test_email,
    preview_template,
    process_interaction,
    slack_command,
    preview_slack_template,
    HooksView,
    get_sample_data,
)

app_name = "notify"
urlpatterns = [
    path("preview/<slug>", preview_template),
    path("preview/slack/<slug>", preview_slack_template),
    path("test/email/<email>", test_email),
    path("slack/interaction", process_interaction),
    path("hook/subscribe", HooksView.as_view()),
    path("hook/subscribe/<int:hook_id>", HooksView.as_view()),
    path("hook/sample", get_sample_data),
    path("hook/<int:hook_id>/sample", get_sample_data),
    path("slack/command", slack_command, name="slack_command"),
]

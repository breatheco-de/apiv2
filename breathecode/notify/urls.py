"""
URL Configuration for Notify App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /me/notifications, /slack/teams
   - Use singular nouns for individual resources: /hook/<id>

2. HTTP Methods:
   - GET /me/notification - List current user's notifications
   - POST /me/notification - Create new notification
   - GET /me/notification/<id> - Get specific notification
   - PUT/PATCH /me/notification/<id> - Update specific notification
   - DELETE /me/notification/<id> - Delete specific notification

3. Nested Resources:
   - /hook/subscribe - Webhook subscriptions
   - /hook/<id>/sample - Sample data for specific hook
   - /slack/command - Slack command endpoints

4. Actions (Non-REST exceptions):
   - /preview/<slug> - Preview notification template (GET)
   - /preview/slack/<slug> - Preview Slack template (GET)
   - /test/email/<email> - Test email delivery (GET)
   - /slack/interaction - Process Slack interactions (POST)

5. Special Endpoints:
   - /me/* - Current user's notifications
   - /hook/* - Webhook-related endpoints
   - /slack/* - Slack integration endpoints
   - /preview/* - Template preview endpoints
   - /test/* - Testing endpoints

6. URL Naming:
   - Use snake_case for URL names: me_notification
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- me_notification - Get/update current user's notifications
- slack_command - Slack command endpoint
- slack_team - Slack team management
"""

from django.urls import path

from .views import (
    AcademyNotifySettingsView,
    AcademyNotifyVariablesView,
    HooksView,
    NotificationTemplatePreviewView,
    NotificationTemplatesView,
    NotificationTemplateView,
    NotificationsView,
    SlackTeamsView,
    get_sample_data,
    preview_slack_template,
    preview_template,
    process_interaction,
    slack_command,
    test_email,
)

app_name = "notify"
urlpatterns = [
    # Template preview endpoints (legacy)
    path("preview/<slug>", preview_template),
    path("preview/slack/<slug>", preview_slack_template),
    path("test/email/<email>", test_email),
    # Notification template management (requires read_notification capability)
    path("academy/template", NotificationTemplatesView.as_view(), name="academy_template"),
    path("academy/template/<str:slug>", NotificationTemplateView.as_view(), name="academy_template_slug"),
    path(
        "academy/template/<str:slug>/preview",
        NotificationTemplatePreviewView.as_view(),
        name="academy_template_slug_preview",
    ),
    # Academy notification settings
    path("academy/settings", AcademyNotifySettingsView.as_view(), name="academy_notify_settings"),
    path("academy/variables", AcademyNotifyVariablesView.as_view(), name="academy_notify_variables"),
    # Slack integration endpoints
    path("slack/interaction", process_interaction),
    path("slack/command", slack_command, name="slack_command"),
    path("slack/team", SlackTeamsView.as_view(), name="slack_team"),
    # Webhook endpoints
    path("hook/subscribe", HooksView.as_view()),
    path("hook/subscribe/<int:hook_id>", HooksView.as_view()),
    path("hook/sample", get_sample_data),
    path("hook/<int:hook_id>/sample", get_sample_data),
    # User notification endpoints
    path("me/notification", NotificationsView.as_view(), name="me_notification"),
]

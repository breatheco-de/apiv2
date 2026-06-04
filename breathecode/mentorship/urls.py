"""
URL Configuration for Mentorship App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /academy/mentors, /academy/sessions
   - Use singular nouns for individual resources: /mentor/<id>

2. HTTP Methods:
   - GET /academy/mentor - List all academy mentors
   - POST /academy/mentor - Create new mentor
   - GET /academy/mentor/<id> - Get specific mentor
   - PUT/PATCH /academy/mentor/<id> - Update specific mentor
   - DELETE /academy/mentor/<id> - Delete specific mentor

3. Nested Resources:
   - /academy/mentor/<id>/session - Sessions for a specific mentor
   - /academy/service/<id>/session - Sessions for a specific service
   - /academy/mentor/<id>/bill - Bills for a specific mentor

4. Actions (Non-REST exceptions):
   - /academy/bill/<id>/html - Render bill as HTML (GET)
   - /calendly/webhook/<hash> - Calendly webhook (POST)

5. Special Endpoints:
   - /user/me/* - Current user's mentorship resources
   - /academy/* - Academy-specific resources
   - /public/* - Publicly accessible endpoints
   - /calendly/* - Calendly integration endpoints

6. URL Naming:
   - Use snake_case for URL names: academy_mentor_id_session
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- academy_mentor_id_session - Get/update sessions for specific mentor
- user_session - Get/update current user's sessions
- academy_service_id_session - Get/update sessions for specific service
- public_mentor - Get public mentor information
"""

from django.urls import path
from .views import (
    ServiceView,
    MentorView,
    SessionView,
    render_html_bill,
    BillView,
    ServiceSessionView,
    MentorSessionView,
    UserMeSessionView,
    UserMeBillView,
    PublicMentorView,
    AgentView,
    SupportChannelView,
    calendly_webhook,
    AcademyCalendlyOrgView,
)

app_name = "mentorship"
urlpatterns = [
    path("academy/service", ServiceView.as_view(), name="academy_service"),
    path("academy/service/<int:service_id>", ServiceView.as_view(), name="academy_service_id"),
    path("academy/mentor", MentorView.as_view(), name="academy_mentor"),
    path("academy/agent", AgentView.as_view(), name="academy_agent"),
    path("academy/supportchannel", SupportChannelView.as_view(), name="academy_supportchannel"),
    path("academy/mentor/<int:mentor_id>", MentorView.as_view(), name="academy_mentor_id"),
    path("academy/mentor/<int:mentor_id>/session", MentorSessionView.as_view(), name="academy_mentor_id_session"),
    path("academy/session", SessionView.as_view(), name="academy_session"),
    path("academy/session/<int:session_id>", SessionView.as_view(), name="academy_session_id"),
    path("academy/service/<int:service_id>/session", ServiceSessionView.as_view(), name="academy_service_id_session"),
    path("academy/bill", BillView.as_view(), name="academy_bill"),
    path("academy/bill/<int:bill_id>", BillView.as_view(), name="academy_bill_id"),
    path("academy/bill/<int:id>/html", render_html_bill, name="academy_bill_id_html"),
    path("academy/mentor/<int:mentor_id>/bill", BillView.as_view(), name="academy_mentor_id_bill"),
    path("user/me/session", UserMeSessionView.as_view(), name="user_session"),
    path("user/me/bill", UserMeBillView.as_view(), name="user_bill"),
    # Public Endpoints for marketing purposes
    path("public/mentor", PublicMentorView.as_view(), name="public_mentor"),
    # hash belongs to the calendly organization
    path("calendly/webhook/<str:org_hash>", calendly_webhook, name="calendly_webhook_id"),
    path("academy/calendly/organization", AcademyCalendlyOrgView.as_view(), name="academy_calendly_organization"),
]

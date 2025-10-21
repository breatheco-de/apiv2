"""
URL Configuration for Events App

This module defines URL patterns following REST conventions with some specific exceptions
for the BreatheCode API v2.

REST Naming Conventions:
========================

1. Resource-based URLs:
   - Use plural nouns for collections: /academy/events, /academy/venues
   - Use singular nouns for individual resources: /event/<id>

2. HTTP Methods:
   - GET /academy/event - List all academy events
   - POST /academy/event - Create new event
   - GET /academy/event/<id> - Get specific event
   - PUT/PATCH /academy/event/<id> - Update specific event
   - DELETE /academy/event/<id> - Delete specific event

3. Nested Resources:
   - /academy/event/<id>/join - Join a specific event
   - /me/event/<id>/checkin - Check in to an event
   - /academy/organization/organizer - Event organizers

4. Actions (Non-REST exceptions):
   - /me/event/<id>/join - Join an event (POST)
   - /me/event/<id>/checkin - Check in to event (POST)
   - /academy/event/<id>/join - Academy event join (POST)

5. Special Endpoints:
   - /me/* - Current user's events and actions
   - /academy/* - Academy-specific resources
   - /ical/* - iCal feed endpoints
   - /feed/* - RSS/Atom feeds
   - /all - Public events listing

6. URL Naming:
   - Use snake_case for URL names: academy_event_id
   - Include resource type and ID when applicable
   - Be descriptive but concise

Examples:
- academy_event_id - Get/update specific academy event
- me_event_id_checkin - Check in to specific event
- academy_organization_organizer_id - Get/update specific organizer
- ical_student_id - Get iCal feed for specific student
"""

from django.urls import path

from .syndication import LatestEventsFeed
from .views import (
    AcademyEventCheckinView,
    AcademyEventJoinView,
    AcademyEventTypeView,
    AcademyEventView,
    AcademyLiveClassJoinView,
    AcademyLiveClassView,
    AcademyOrganizationOrganizerView,
    AcademyOrganizationView,
    AcademyOrganizerView,
    AcademyVenueView,
    EventCheckinView,
    EventMeCheckinView,
    EventMeView,
    EventPublicView,
    EventTypeView,
    EventTypeVisibilitySettingView,
    EventView,
    ICalCohortsView,
    ICalEventView,
    ICalStudentView,
    MeLiveClassView,
    OrganizationWebhookView,
    UserEventCheckinView,
    eventbrite_webhook,
    get_events,
    join_event,
    join_live_class,
    live_workshop_status,
)

app_name = "events"
urlpatterns = [
    path("", EventView.as_view(), name="root"),
    path("me", EventMeView.as_view(), name="me"),
    path("me/event/checkin", UserEventCheckinView.as_view(), name="me_event_checkin"),
    path("me/event/<int:event_id>/checkin", EventMeCheckinView.as_view(), name="me_event_id_checkin"),
    path("me/event/<int:event_id>/join", join_event, name="me_event_id_join"),
    path("me/event/<int:event_id>", EventMeView.as_view(), name="me_event_id"),
    # move this
    path("me/event/liveclass", MeLiveClassView.as_view(), name="me_event_liveclass"),
    path("me/event/liveclass/join/<str:hash>", join_live_class, name="me_event_liveclass_join_hash"),
    path("academy/event/liveclass", AcademyLiveClassView.as_view(), name="academy_event_liveclass"),
    path(
        "academy/event/liveclass/join/<str:hash>",
        AcademyLiveClassJoinView.as_view(),
        name="academy_event_liveclass_join_hash",
    ),
    path("all", get_events, name="all"),
    path("feed/all", LatestEventsFeed()),
    path("event/<slug:event_slug>", EventPublicView.as_view(), name="event"),
    path("eventype", EventTypeView.as_view(), name="eventype"),
    path("event/<int:event_id>/checkin", EventCheckinView.as_view(), name="event_checkin"),
    path("academy/event", AcademyEventView.as_view(), name="academy_event"),
    path("academy/event.csv", AcademyEventView.as_view(), name="academy_event_csv"),
    path("academy/event/<int:event_id>", AcademyEventView.as_view(), name="academy_event_id"),
    path("academy/event/<int:event_id>/join", AcademyEventJoinView.as_view(), name="academy_event_id_join"),
    path("academy/organization", AcademyOrganizationView.as_view(), name="academy_organization"),
    path(
        "academy/organization/organizer",
        AcademyOrganizationOrganizerView.as_view(),
        name="academy_organization_organizer",
    ),
    path(
        "academy/organization/organizer/<int:organizer_id>",
        AcademyOrganizationOrganizerView.as_view(),
        name="academy_organization_organizer_id",
    ),
    path("academy/organizer", AcademyOrganizerView.as_view(), name="academy_organizer"),
    path(
        "academy/organization/eventbrite/webhook",
        OrganizationWebhookView.as_view(),
        name="academy_organizarion_eventbrite_webhook",
    ),
    path("ical/cohorts", ICalCohortsView.as_view(), name="ical_cohorts"),
    path("ical/events", ICalEventView.as_view(), name="ical_events"),
    path("ical/student/<int:user_id>", ICalStudentView.as_view(), name="ical_student_id"),
    path("academy/venues", AcademyVenueView.as_view(), name="academy_venues"),
    path("academy/eventype", AcademyEventTypeView.as_view(), name="academy_eventype"),
    path("academy/eventype/<slug:event_type_slug>", AcademyEventTypeView.as_view(), name="academy_eventype_slug"),
    path(
        "academy/eventype/<slug:event_type_slug>/visibilitysetting",
        EventTypeVisibilitySettingView.as_view(),
        name="academy_eventype_slug_visibilitysetting",
    ),
    path(
        "academy/eventype/<slug:event_type_slug>/visibilitysetting/<int:visibility_setting_id>",
        EventTypeVisibilitySettingView.as_view(),
        name="academy_eventype_slug_visibilitysetting_id",
    ),
    path("academy/checkin", AcademyEventCheckinView.as_view(), name="academy_checkin"),
    path("academy/checkin.csv", AcademyEventCheckinView.as_view(), name="academy_checkin_csv"),
    path("eventbrite/webhook/<int:organization_id>", eventbrite_webhook, name="eventbrite_webhook_id"),
    path("live-workshop-status", live_workshop_status, name="live_workshop_status"),
]

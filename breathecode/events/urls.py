from django.urls import path
from .views import (EventView, EventTypeView, EventCheckinView, get_events, eventbrite_webhook,
                    AcademyEventView, AcademyVenueView, ICalCohortsView, ICalEventView, ICalStudentView,
                    AcademyOrganizationView, OrganizationWebhookView, AcademyOrganizerView,
                    AcademyOrganizationOrganizerView)

app_name = 'events'
urlpatterns = [
    path('', EventView.as_view(), name='root'),
    path('all', get_events, name='all'),
    path('academy/event', AcademyEventView.as_view(), name='academy_event'),
    path('academy/organization', AcademyOrganizationView.as_view(), name='academy_organization'),
    path('academy/organization/organizer',
         AcademyOrganizationOrganizerView.as_view(),
         name='academy_organization_organizer'),
    path('academy/organization/organizer/<int:organizer_id>',
         AcademyOrganizationOrganizerView.as_view(),
         name='academy_organization_organizer_id'),
    path('academy/organizer', AcademyOrganizerView.as_view(), name='academy_organizer'),
    path('academy/organization/eventbrite/webhook',
         OrganizationWebhookView.as_view(),
         name='academy_organizarion_eventbrite_webhook'),
    path('ical/cohorts', ICalCohortsView.as_view(), name='ical_cohorts'),
    path('ical/events', ICalEventView.as_view(), name='ical_events'),
    path('ical/student/<int:user_id>', ICalStudentView.as_view(), name='ical_student_id'),
    path('academy/venues', AcademyVenueView.as_view(), name='academy_venues'),
    path('academy/event/<int:event_id>', AcademyEventView.as_view(), name='academy_event_id'),
    path('academy/eventype', EventTypeView.as_view(), name='type'),
    path('academy/checkin', EventCheckinView.as_view(), name='academy_checkin'),
    path('eventbrite/webhook/<int:organization_id>', eventbrite_webhook, name='eventbrite_webhook_id'),
]

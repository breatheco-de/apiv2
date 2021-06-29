from django.urls import path
from .views import (EventView, EventTypeView, EventCheckinView, get_events,
                    eventbrite_webhook, AcademyEventView, AcademyVenueView,
                    ICalCohortsView, ICalEventView, ICalStudentView)

app_name = 'events'
urlpatterns = [
    path('', EventView.as_view(), name='root'),
    path('all', get_events, name='all'),
    path('academy/event',
         AcademyEventView.as_view(),
         name="academy_all_events"),
    path('ical/cohorts',
         ICalCohortsView.as_view(),
         name="academy_id_ical_cohorts"),  # don't correct that name
    path('ical/events', ICalEventView.as_view(),
         name="academy_id_ical_events"),  # don't correct that name
    path('ical/student/<int:user_id>',
         ICalStudentView.as_view(),
         name="ical_student_id"),  # don't correct that name
    path('academy/venues', AcademyVenueView.as_view(), name="academy_venues"),
    path('academy/event/<int:event_id>',
         AcademyEventView.as_view(),
         name="academy_single_event"),
    path('academy/eventype', EventTypeView.as_view(), name='type'),
    path('academy/checkin', EventCheckinView.as_view(),
         name='academy_checkin'),
    path('eventbrite/webhook/<int:organization_id>',
         eventbrite_webhook,
         name='eventbrite_webhook_id'),
]

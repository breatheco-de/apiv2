from django.urls import path
from .views import (
    EventView, EventTypeView, EventCheckinView, get_events, eventbrite_webhook,
    AcademyEventView, AcademyVenueView, AcademyICalCohortsView
)

app_name = 'events'
urlpatterns = [
    path('', EventView.as_view(), name='root'),
    path('all', get_events, name='all'),
    path('academy/event', AcademyEventView.as_view(), name="academy_all_events"),
    path('academy/ical/cohorts', AcademyICalCohortsView.as_view(), name="academy_id_ical_cohorts"),
    path('academy/venues', AcademyVenueView.as_view(), name="academy_venues"),
    path('academy/event/<int:event_id>',
         AcademyEventView.as_view(), name="academy_single_event"),
    path('academy/eventype', EventTypeView.as_view(), name='type'),
    path('academy/checkin', EventCheckinView.as_view(), name='academy_checkin'),
    path('eventbrite/webhook/<int:organization_id>', eventbrite_webhook,
         name='eventbrite_webhook_id'),
]

from django.contrib import admin
from django.urls import path, include
from .views import ( 
    EventView, EventTypeView, EventCheckinView, get_events, eventbrite_webhook,
    AcademyEventView
)

app_name='events'
urlpatterns = [
    path('', EventView.as_view(), name='root'),
    path('all', get_events, name='all'),
    path('academy/event', AcademyEventView.as_view()),
    path('academy/event/<int:event_id>', AcademyEventView.as_view()),
    path('type/', EventTypeView.as_view(), name='type'),
    path('academy/checkin', EventCheckinView.as_view(), name='checkin'),
    path('eventbrite/webhook/<int:organization_id>', eventbrite_webhook,
        name='eventbrite_webhook_id'),
]

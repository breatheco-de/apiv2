from django.contrib import admin
from django.urls import path, include
from .views import EventView, EventTypeView, EventCheckinView, get_events

app_name='events'
urlpatterns = [
    path('', EventView.as_view()),
    path('all', get_events),
    path('type/', EventTypeView.as_view()),
    path('checkin/', EventCheckinView.as_view()),
]


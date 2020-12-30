from django.contrib import admin
from django.urls import path, include
from .views import EventView, EventTypeView, EventCheckinView, get_events

app_name='events'
urlpatterns = [
    path('', EventView.as_view(), name='root'),
    path('all', get_events, name='all'),
    path('type/', EventTypeView.as_view(), name='type'),
    path('checkin/', EventCheckinView.as_view(), name='checkin'),
]

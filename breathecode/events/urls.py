from django.contrib import admin
from django.urls import path, include
from .views import EventView, EventTypeView, EventCheckinView

app_name='events'
urlpatterns = [
    path('', EventView.as_view()),
    path('type/', EventTypeView.as_view()),
    path('checkin/', EventCheckinView.as_view()),
]


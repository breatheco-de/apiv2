from django.contrib import admin
from django.urls import path, include
from .views import ActivityView

app_name='activity'
urlpatterns = [
    path('activity/', ActivityView.as_view()),
]


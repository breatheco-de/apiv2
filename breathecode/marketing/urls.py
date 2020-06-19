from django.contrib import admin
from django.urls import path, include
from .views import create_lead, sync_tags_with_active_campaign, sync_automations_with_active_campaign
from rest_framework.authtoken import views

app_name='events'
urlpatterns = [
    path('lead', create_lead),
    path('tag/sync', sync_tags_with_active_campaign),
    path('automation/sync', sync_automations_with_active_campaign),
]


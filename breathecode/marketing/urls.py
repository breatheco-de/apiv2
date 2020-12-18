from django.contrib import admin
from django.urls import path, include
from .views import ( 
    create_lead, sync_tags_with_active_campaign, sync_automations_with_active_campaign,
    receive_facebook_lead
)
from rest_framework.authtoken import views

app_name='marketing'
urlpatterns = [
    path('lead', create_lead),
    path('academy/<int:academy_id>/tag/sync', sync_tags_with_active_campaign),
    path('academy/<int:academt_id>/automation/sync', sync_automations_with_active_campaign),
    
    path('facebook/lead', receive_facebook_lead),
]


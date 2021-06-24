from django.contrib import admin
from django.urls import path, include
from .views import (create_lead, sync_tags_with_active_campaign,
                    sync_automations_with_active_campaign,
                    receive_facebook_lead, redirect_link)
from rest_framework.authtoken import views

app_name = 'marketing'
urlpatterns = [
    path('<str:link_slug>', redirect_link),
]

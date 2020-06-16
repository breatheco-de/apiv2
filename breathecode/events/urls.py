from django.contrib import admin
from django.urls import path, include
from breathecode.authenticate.views import get_users, get_groups, CustomAuthToken, get_github_token, save_github_token
from rest_framework.authtoken import views

app_name='events'
urlpatterns = [
    path('v1/event/', get_users),
]


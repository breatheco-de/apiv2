from django.contrib import admin
from django.urls import path, include
from .views import get_apps, get_endpoints

app_name = 'monitoring'
urlpatterns = [
    path('application/', get_apps),
    path('endpoint/', get_endpoints),
]

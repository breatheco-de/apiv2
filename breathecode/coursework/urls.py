from django.contrib import admin
from django.urls import path, include
from .views import get_courses
from rest_framework.authtoken import views

app_name='events'
urlpatterns = [
    path('/course', get_courses),
]


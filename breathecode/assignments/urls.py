from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from .views import TaskView

app_name = 'assignments'
urlpatterns = [
    path('task/', TaskView.as_view()),
]

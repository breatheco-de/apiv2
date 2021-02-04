from django.contrib import admin
from django.urls import path, include
from .views import ActivityView, CohortActivityView

app_name='activity'
urlpatterns = [
    path('activity/', ActivityView.as_view()),
    path('cohort/<str:cohort_slug>', CohortActivityView.as_view()),
]


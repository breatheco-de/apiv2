from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from .views import (
    AcademyView, CohortUserView, CertificateView, get_cohorts, AcademyCohortView,
    get_timezones, UserView, UserMeView
)

app_name = 'admissions'
urlpatterns = [
    path('academy/', AcademyView.as_view(), name="academy"),
    path('academy/cohort', AcademyCohortView.as_view(), name="academy_cohort"),
    path('academy/cohort/<str:cohort_id>', AcademyCohortView.as_view(), name="academy_cohort_id"),
    path('cohort/all', get_cohorts, name="cohort_all"),
    path('cohort/user', CohortUserView.as_view(), name="cohort_user"),
    path('user/me', UserMeView.as_view(), name="user_me"),
    path('user', UserView.as_view(), name="user"),

    # update a cohort user information
    path('cohort/<int:cohort_id>/user/<int:user_id>', CohortUserView.as_view(),
        name="cohort_id_user_id"),
    path('cohort/<int:cohort_id>/user', CohortUserView.as_view(), name="cohort_id_user"),
    path('certificate/', CertificateView.as_view(), name="certificate"),
    
    path('catalog/timezones', get_timezones, name="timezones_all"),
]

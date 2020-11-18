from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from .views import (
    AcademyView, CohortUserView, CertificateView, CohortView, get_cohorts
)

app_name = 'admissions'
urlpatterns = [
    path('academy/', AcademyView.as_view(), name="academy"),
    path('cohort/', CohortView.as_view(), name="cohort"),
    path('cohort/all', get_cohorts, name="cohort_all"),
    path('cohort/user/', CohortUserView.as_view(), name="cohort_user"),

    # update a cohort user information
    path('cohort/<int:cohort_id>/user/<int:user_id>', CohortUserView.as_view(),
        name="cohort_id_user_id"),
    path('cohort/<str:cohort_id>', CohortView.as_view(), name="cohort_id"),
    path('certificate/', CertificateView.as_view(), name="certificate"),
]

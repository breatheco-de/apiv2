from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from .views import (
    AcademyView, CohortUserView, CertificateView, CohortView, get_cohorts
)

app_name = 'admissions'
urlpatterns = [
    path('academy/', AcademyView.as_view()),
    path('cohort/', CohortView.as_view()),
    path('cohort/all', get_cohorts),
    # path('cohort/user/', CohortUserView.as_view()),
    path('cohort/user/', CohortUserView.as_view()),
    
    # update a cohort user information
    path('cohort/<int:cohort_id>/user/<int:user_id>', CohortUserView.as_view()),
    
    path('cohort/<str:cohort_id>', CohortView.as_view()),
    
    path('certificate/', CertificateView.as_view()),
]

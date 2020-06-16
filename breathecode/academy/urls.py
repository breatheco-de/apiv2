from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from .views import AcademyView, CohortUserView, CertificateView, CohortView

app_name = 'academy'
urlpatterns = [
    path('academy/', AcademyView.as_view()),
    path('cohort/', CohortView.as_view()),
    path('cohort/user/', CohortUserView.as_view()),
    path('certificate/', CertificateView.as_view()),
]

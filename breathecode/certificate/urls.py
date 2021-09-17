from django.contrib import admin
from django.urls import path, include
from .views import (get_specialties, get_badges, get_certificate, CertificateView, CertificateCohortView,
                    CertificateAcademyView, LayoutView)
from rest_framework.authtoken import views

app_name = 'certificate'
urlpatterns = [
    path('specialty', get_specialties),
    path('badge', get_badges),
    path('academy/layout', LayoutView.as_view()),
    path('token/<str:token>/', get_certificate),
    path('cohort/<int:cohort_id>/student/<int:student_id>',
         CertificateView.as_view(),
         name='cohort_id_student_id'),
    path('cohort/<int:cohort_id>', CertificateCohortView.as_view(), name='cohort_id'),
    path('', CertificateAcademyView.as_view(), name='root'),
]

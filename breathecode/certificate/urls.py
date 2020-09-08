from django.contrib import admin
from django.urls import path, include
from .views import get_specialties, get_badges, get_certificate
from rest_framework.authtoken import views

app_name='certificate'
urlpatterns = [
    path('specialty', get_specialties),
    path('badge', get_badges),
    path('token/<str:token>/', get_certificate),
    # path('course/<str:course_slug>/', get_single_course),
    # path('course/<str:course_slug>/syllabus', SyllabusView.as_view()),
    # path('course/<str:course_slug>/syllabus/<int:version>', SyllabusView.as_view()),
]


from django.contrib import admin
from django.urls import path, include
from .views import get_courses, get_single_course, SyllabusView
from rest_framework.authtoken import views

app_name='coursework'
urlpatterns = [
    path('course', get_courses),
    path('course/<str:course_slug>/', get_single_course),
    path('course/<str:course_slug>/syllabus', SyllabusView.as_view()),
    path('course/<str:course_slug>/syllabus/<int:version>', SyllabusView.as_view()),
]


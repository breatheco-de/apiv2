from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from .views import (
    AcademyView, CohortUserView, get_cohorts, AcademyCohortView,
    get_timezones, UserView, UserMeView, AcademyCohortUserView,
    get_courses, get_single_course, SyllabusView
)

app_name = 'admissions'
urlpatterns = [
    #depcrecated methods, soon to be deleted
    path('cohort/all', get_cohorts, name="cohort_all"),
    path('cohort/user', CohortUserView.as_view(), name="cohort_user"),
    path('cohort/<int:cohort_id>/user/<int:user_id>', CohortUserView.as_view(),
        name="cohort_id_user_id"),
    path('cohort/<int:cohort_id>/user', CohortUserView.as_view(), name="cohort_id_user"),

    # new endpoints (replacing above)
    path('academy/cohort/user', AcademyCohortUserView.as_view()),
    path('academy/cohort/<str:cohort_id>', AcademyCohortView.as_view(), name="academy_cohort_id"),
    path('academy/cohort/<int:cohort_id>/user/<int:user_id>', AcademyCohortUserView.as_view()),
    path('academy/cohort/<int:cohort_id>/user', AcademyCohortUserView.as_view()),

    path('academy/', AcademyView.as_view(), name="academy"),
    path('academy/cohort', AcademyCohortView.as_view(), name="academy_cohort"),
    path('user/me', UserMeView.as_view(), name="user_me"),
    path('user', UserView.as_view(), name="user"),

    # update a cohort user information
    path('certificate', get_courses, name="certificate"),
    path('certificate/<str:certificate_slug>/', get_single_course),
    path('certificate/<str:certificate_slug>/syllabus', SyllabusView.as_view()),
    path('certificate/<str:certificate_slug>/syllabus/<int:version>', SyllabusView.as_view()),
    path('certificate/<str:certificate_slug>/academy/<int:academy_id>/syllabus/<int:version>', SyllabusView.as_view()),
    path('certificate/<str:certificate_slug>/academy/<int:academy_id>/syllabus', SyllabusView.as_view()),

    path('catalog/timezones', get_timezones, name="timezones_all"),
]

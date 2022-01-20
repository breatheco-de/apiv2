from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from .views import (TaskMeView, sync_cohort_tasks_view, TaskTeacherView, deliver_assignment_view,
                    TaskMeDeliverView)

app_name = 'assignments'
urlpatterns = [
    path('task/', TaskTeacherView.as_view()),
    path('user/me/task', TaskMeView.as_view()),
    path('user/<int:user_id>/task', TaskMeView.as_view()),
    path('user/<int:user_id>/task/<int:task_id>', TaskMeView.as_view()),
    path('academy/user/<int:user_id>/task', TaskMeView.as_view()),
    path('task/<int:task_id>/deliver/<str:token>', deliver_assignment_view),
    path('task/<int:task_id>/deliver', TaskMeDeliverView.as_view()),
    path('task/<int:task_id>', TaskMeView.as_view(), name='task_id'),
    path('sync/cohort/<int:cohort_id>/task', sync_cohort_tasks_view),
]

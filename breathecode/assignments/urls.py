from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from .views import TaskMeView, sync_cohort_tasks_view, TaskTeacherView

app_name = 'assignments'
urlpatterns = [
    path('task', TaskTeacherView),
    # path('user/me/task', TaskMeView.as_view()),
    # path('user/<int:user_id>/task', TaskMeView.as_view()),
    # path('academy/user/<int:user_id>/task', TaskMeView.as_view()),
    # path('task/<int:task_id>', TaskMeView.as_view()),
    # path('sync/cohort/<int:cohort_id>/task', sync_cohort_tasks_view),
]

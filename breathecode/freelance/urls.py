from django.contrib import admin
from django.urls import path, include
from .views import BillView, sync_user_issues
from rest_framework.authtoken import views

app_name='freelance'
urlpatterns = [
    path('bills', BillView.as_view()),
    path('sync/user', sync_user_issues),
]


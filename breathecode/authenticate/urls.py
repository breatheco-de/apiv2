"""breathecode URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from .views import (
    get_users, get_users_me, get_groups, CustomAuthToken, get_github_token, save_github_token
)
from rest_framework.authtoken import views

app_name='authenticate'
urlpatterns = [
    path('user/', get_users, name="user"),
    path('user/me', get_users_me, name="user_me"),
    path('group/', get_groups),
    path('token/', CustomAuthToken.as_view()),
    path('github/', get_github_token),
    path('github/callback/', save_github_token),
]


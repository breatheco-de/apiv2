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
# from django.contrib import admin
# from rest_framework.authtoken import views
from django.urls import path
from .views import (
    get_users, get_users_me, LoginView, LogoutView,TemporalTokenView , get_github_token,
    save_github_token, get_slack_token, save_slack_token, pick_password, change_password,
    get_token_info, get_facebook_token, save_facebook_token, StaffView
)

app_name='authenticate'
urlpatterns = [
    path('user/', get_users, name="user"),
    path('user/me', get_users_me, name="user_me"),
    path('user/staff', StaffView.as_view()),
    path('user/staff/<int:user_id>/academy/<int:academy_id>', StaffView.as_view()),
    # path('group/', get_groups, name="group"),
    path('login/', LoginView.as_view(), name="login"),
    path('logout/', LogoutView.as_view(), name="logout"),
    path('token/', TemporalTokenView.as_view(), name="token"),
    path('token/<str:token>', get_token_info, name="token"),

    path('password/<str:token>', pick_password, name="password_token"),
    path('password/form', change_password, name="password_form"),

    path('github/', get_github_token, name="github"),
    path('github/callback/', save_github_token, name="github_callback"),

    path('slack/', get_slack_token, name="slack"),
    path('slack/callback/', save_slack_token, name="slack_callback"),
    
    path('facebook/', get_facebook_token, name="facebook"),
    path('facebook/callback/', save_facebook_token, name="facebook_callback"),
]

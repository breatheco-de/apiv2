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
    get_users, UserMeView, LoginView, LogoutView,TemporalTokenView , get_github_token,
    save_github_token, get_slack_token, save_slack_token, pick_password, change_password,
    get_token_info, get_facebook_token, save_facebook_token, MemberView, reset_password_view,
    login_html_view, StudentView, render_invite, get_roles
)

app_name='authenticate'
urlpatterns = [
    path('user/', get_users, name="user"),
    path('role', get_roles, name="role"),
    path('user/me', UserMeView.as_view(), name="user_me"),
    path('user/invite/<str:token>', render_invite, name="academy_invite"),
    
    path('academy/member', MemberView.as_view()),
    path('academy/member/<int:user_id>', MemberView.as_view()),
    path('academy/student', StudentView.as_view()),
    path('academy/student/<int:user_id>', StudentView.as_view()),
    # path('group/', get_groups, name="group"),

    path('view/login', login_html_view, name="login_view"), # html login form
    path('login/', LoginView.as_view(), name="login"), # get token from email and password
    path('logout/', LogoutView.as_view(), name="logout"),
    path('token/', TemporalTokenView.as_view(), name="token"), # get a another token (temporal), from a logged in user
    path('token/<str:token>', get_token_info, name="token"), # get token information

    path('password/reset', reset_password_view, name="password_reset"),
    path('password/<str:token>', pick_password, name="password_token"),

    path('github/', get_github_token, name="github"),
    path('github/callback/', save_github_token, name="github_callback"),

    path('slack/', get_slack_token, name="slack"),
    path('slack/callback/', save_slack_token, name="slack_callback"),
    
    path('facebook/', get_facebook_token, name="facebook"),
    path('facebook/callback/', save_facebook_token, name="facebook_callback"),
]

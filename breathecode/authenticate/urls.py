"""breathecode URL Configuration

The `urlpatterns` list routes URLsimage.png to views. For more information please see:
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

import os

from django.urls import path
from linked_services.rest_framework.views import app_webhook, authorize_view

from breathecode.authenticate.actions import get_user_language

from .views import (
    AcademyAuthSettingsView,
    AcademyGithubSyncView,
    AcademyInviteView,
    AcademyTokenView,
    AppSync,
    AppUserAgreementView,
    AppUserView,
    ConfirmEmailView,
    GithubMeView,
    GithubUserView,
    GitpodUserView,
    LoginView,
    LogoutView,
    MeInviteView,
    MemberView,
    PasswordResetView,
    ProfileInviteMeView,
    ProfileMePictureView,
    ProfileMeView,
    ProfileView,
    ResendInviteView,
    StudentView,
    TemporalTokenView,
    TokenTemporalView,
    UserMeView,
    UserSettingsView,
    WaitingListView,
    get_facebook_token,
    get_github_token,
    get_google_token,
    get_roles,
    get_slack_token,
    get_token_info,
    get_user_by_id_or_email,
    get_users,
    login_html_view,
    pick_password,
    render_academy_invite,
    render_invite,
    render_user_invite,
    reset_password_view,
    save_facebook_token,
    save_github_token,
    save_google_token,
    save_slack_token,
    sync_gitpod_users_view,
)

# avoiding issues on test environment due that the fixture are loaded after this app
ENV = os.getenv("ENV")
TEST_ENV = ENV == "test" or ENV not in ["development", "staging", "production"]
LOGIN_URL = "/v1/auth/view/login"
app_url = os.getenv("APP_URL")

if TEST_ENV and not app_url:
    import faker

    fake = faker.Faker()

    app_url = fake.url().replace("http://", "https://")

app_name = "authenticate"
urlpatterns = [
    path("confirmation/<str:token>", ConfirmEmailView.as_view(), name="confirmation_token"),
    path("invite/resend/<int:invite_id>", ResendInviteView.as_view(), name="invite_resend_id"),
    path("member/invite/resend/<int:invite_id>", AcademyInviteView.as_view(), name="member_invite_resend_id"),
    path("subscribe/", WaitingListView.as_view(), name="subscribe"),
    path("user/", get_users, name="user"),
    path("user/me", UserMeView.as_view(), name="user_me"),
    path("user/me/settings", UserSettingsView.as_view(), name="user_me_settings"),
    path("user/<str:id_or_email>", get_user_by_id_or_email),
    path("role", get_roles, name="role"),
    path("role/<str:role_slug>", get_roles, name="role_slug"),
    path("profile/<int:user_id>", ProfileView.as_view(), name="user_profile"),
    path("profile/me", ProfileMeView.as_view(), name="profile_me"),
    path("profile/me/picture", ProfileMePictureView.as_view(), name="profile_me_picture"),
    path("profile/invite/me", ProfileInviteMeView.as_view(), name="profile_invite_me"),
    path("member/invite", render_user_invite, name="member_invite"),
    path("member/invite/<str:token>", render_invite, name="member_invite_token"),
    path(
        "member/<int:profile_academy_id>/token", TokenTemporalView.as_view(), name="profile_academy_reset_github_link"
    ),
    path("academy/member", MemberView.as_view(), name="academy_member"),
    path("academy/member/<int:profileacademy_id>/invite", AcademyInviteView.as_view(), name="academy_member_id_invite"),
    path("academy/<int:academy_id>/member", MemberView.as_view(), name="academy_id_member"),
    path("academy/<int:academy_id>/member/<str:user_id_or_email>", MemberView.as_view(), name="academy_id_member_id"),
    path("academy/member/<str:user_id_or_email>", MemberView.as_view(), name="academy_member_id"),
    path("academy/student", StudentView.as_view(), name="academy_student"),
    path("academy/student/<str:user_id_or_email>", StudentView.as_view(), name="academy_student_id"),
    # TODO: these endpoints starts with academy but actually they are related to the user, not to the academy
    path("academy/user/me/invite", MeInviteView.as_view(), name="academy_user_me_invite"),
    path("academy/user/me/invite/<slug:new_status>", MeInviteView.as_view(), name="academy_user_me_invite_status"),
    # 🔼🔼🔼
    path("academy/invite/<int:invite_id>", AcademyInviteView.as_view(), name="academy_invite_id"),
    path("academy/user/invite", AcademyInviteView.as_view(), name="academy_user_invite"),
    path("academy/html/invite", render_academy_invite, name="academy_html_invite"),
    # path('group/', get_groups, name="group"),
    path("view/login", login_html_view, name="login_view"),  # html login form
    # get token from email and password
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # get an another token (temporal), from a logged in user
    path("academy/token/", AcademyTokenView.as_view(), name="academy_token"),
    path("token/me", TemporalTokenView.as_view(), name="token_me"),
    path("token/<str:token>", get_token_info, name="token"),  # get token information
    path("password/reset", reset_password_view, name="password_reset"),
    path("member/<int:profileacademy_id>/password/reset", PasswordResetView.as_view(), name="member_password_reset"),
    path("password/<str:token>", pick_password, name="password_token"),
    path("github/", get_github_token, name="github"),
    path("github/me", GithubMeView.as_view(), name="github_me"),
    path("github/<str:token>", get_github_token, name="github_token"),
    path("github/callback/", save_github_token, name="github_callback"),
    path("slack/", get_slack_token, name="slack"),
    path("slack/callback/", save_slack_token, name="slack_callback"),
    path("facebook/", get_facebook_token, name="facebook"),
    path("facebook/callback/", save_facebook_token, name="facebook_callback"),
    path("user/me", UserMeView.as_view(), name="user_me"),
    path("user/me/invite", MeInviteView.as_view(), name="user_me_invite"),
    path("user/me/invite/<slug:new_status>", MeInviteView.as_view(), name="user_me_invite_status"),
    path("academy/settings", AcademyAuthSettingsView.as_view(), name="academy_me_settings"),
    # google authentication oath2.0
    path("google/<str:token>", get_google_token, name="google_token"),
    path("google/callback/", save_google_token, name="google_callback"),
    path("gitpod/sync", sync_gitpod_users_view, name="sync_gitpod_users"),
    # sync with gitHUB
    path("academy/github/user", GithubUserView.as_view(), name="github_user"),
    path("academy/github/user/sync", AcademyGithubSyncView.as_view(), name="github_user_sync"),
    path("academy/github/user/<int:githubuser_id>", GithubUserView.as_view(), name="github_user_id"),
    # sync with gitPOD
    path("academy/gitpod/user", GitpodUserView.as_view(), name="gitpod_user"),
    path("academy/gitpod/user/<int:gitpoduser_id>", GitpodUserView.as_view(), name="gitpod_user_id"),
    # authorize
    path(
        "authorize/<str:app_slug>",
        authorize_view(login_url=LOGIN_URL, app_url=app_url, get_language=get_user_language),
        name="authorize_slug",
    ),
    # apps
    path("appuseragreement", AppUserAgreementView.as_view(), name="appuseragreement"),
    path("app/user", AppUserView.as_view(), name="app_user"),
    path("app/user/<int:user_id>", AppUserView.as_view(), name="app_user_id"),
    path("app/webhook", app_webhook, name="app_webhook"),
    path("me/app/<str:app_slug>/sync", AppSync.as_view(), name="me_app_slug_sync"),
]

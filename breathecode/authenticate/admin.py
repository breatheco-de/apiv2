import base64, os, urllib.parse, logging
from django.contrib import admin
from urllib.parse import urlparse
from django.contrib.auth.admin import UserAdmin
from .actions import delete_tokens
from django.utils.html import format_html
from .models import (CredentialsGithub, Token, UserProxy, Profile,
                     CredentialsSlack, ProfileAcademy, Role,
                     CredentialsFacebook, Capability, UserInvite)
from .actions import reset_password

logger = logging.getLogger(__name__)


def clean_all_tokens(modeladmin, request, queryset):
    user_ids = queryset.values_list('id', flat=True)
    count = delete_tokens(users=user_ids, status='all')


clean_all_tokens.short_description = "Delete all tokens"


def clean_expired_tokens(modeladmin, request, queryset):
    user_ids = queryset.values_list('id', flat=True)
    count = delete_tokens(users=user_ids, status='expired')


clean_expired_tokens.short_description = "Delete EXPIRED tokens"


def send_reset_password(modeladmin, request, queryset):
    reset_password(users=queryset)


send_reset_password.short_description = "Send reset password link"


@admin.register(CredentialsGithub)
class CredentialsGithubAdmin(admin.ModelAdmin):
    list_display = ('github_id', 'user_id', 'email', 'token')
    search_fields = [
        'user__first_name', 'user__last_name', 'user__email', 'email'
    ]
    raw_id_fields = ["user"]


@admin.register(CredentialsSlack)
class CredentialsSlackAdmin(admin.ModelAdmin):
    list_display = ('user', 'app_id', 'bot_user_id', 'team_id', 'team_name')
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    raw_id_fields = ["user"]


@admin.register(CredentialsFacebook)
class CredentialsFacebookAdmin(admin.ModelAdmin):
    list_display = ('facebook_id', 'user', 'email', 'academy', 'expires_at')


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'token_type', 'expires_at', 'user')
    raw_id_fields = ["user"]

    def get_readonly_fields(self, request, obj=None):
        return ['key']


@admin.register(UserInvite)
class UserInviteAdmin(admin.ModelAdmin):
    search_fields = ['email', 'first_name', 'last_name']
    list_filter = ['academy', 'cohort', 'role']
    list_display = ('email', 'first_name', 'last_name', 'status', 'academy',
                    'token', 'created_at', 'invite_url')

    def invite_url(self, obj):
        params = {"callback": "https://learn.breatheco.de"}
        querystr = urllib.parse.urlencode(params)
        url = os.getenv('API_URL') + "/v1/auth/member/invite/" + str(
            obj.token) + "?" + querystr
        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='{url}'>invite url</a>"
        )


def clear_user_password(modeladmin, request, queryset):
    for u in queryset:
        u.set_unusable_password()
        u.save()


clear_user_password.short_description = "Clear user password"


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff',
                    'github_login')
    actions = [
        clean_all_tokens, clean_expired_tokens, send_reset_password,
        clear_user_password
    ]

    def get_queryset(self, request):

        self.github_callback = f"https://app.breatheco.de"
        self.github_callback = str(
            base64.urlsafe_b64encode(self.github_callback.encode("utf-8")),
            "utf-8")
        return super(UserAdmin, self).get_queryset(request)

    def github_login(self, obj):
        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='/v1/auth/github/?user={obj.id}&url={self.github_callback}'>connect github</a>"
        )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')


@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ('slug', 'description')


def mark_as_active(modeladmin, request, queryset):
    aca_profs = queryset.all()
    for ap in aca_profs:
        ap.status = 'ACTIVE'
        ap.save()

    logger.info(f"All AcademyProfiles marked as ACTIVE")


mark_as_active.short_description = "Mark as ACTIVE"


@admin.register(ProfileAcademy)
class ProfileAcademyAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'academy', 'role', 'status', 'created_at',
                    'slack', 'facebook')
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    list_filter = ['academy__slug', 'status', 'role__slug']
    actions = [mark_as_active]
    raw_id_fields = ["user"]

    def get_queryset(self, request):

        self.slack_callback = f"https://app.breatheco.de"
        self.slack_callback = str(
            base64.urlsafe_b64encode(self.slack_callback.encode("utf-8")),
            "utf-8")
        return super(ProfileAcademyAdmin, self).get_queryset(request)

    def slack(self, obj):
        if obj.user is not None:
            return format_html(
                f"<a rel='noopener noreferrer' target='_blank' href='/v1/auth/slack/?a={obj.academy.id}&user={obj.user.id}&url={self.slack_callback}'>slack login</a>"
            )
        else:
            return "Pending invite response"

    def facebook(self, obj):
        if obj.user is not None:
            return format_html(
                f"<a rel='noopener noreferrer' target='_blank' href='/v1/auth/facebook/?a={obj.academy.id}&user={obj.user.id}&url={self.slack_callback}'>facebook login</a>"
            )
        else:
            return "Pending invite response"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'github_username', 'avatar_url')
    # actions = [clean_all_tokens, clean_expired_tokens, send_reset_password]

import base64
import datetime
import logging
import os
import urllib.parse

from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.html import format_html

import breathecode.marketing.actions as marketing_actions
from breathecode.utils.admin import change_field
from breathecode.utils.datetime_integer import from_now

from . import tasks
from .actions import (
    delete_tokens,
    generate_academy_token,
    reset_password,
    set_gitpod_user_expiration,
    sync_organization_members,
)
from .models import (
    AcademyAuthSettings,
    AcademyProxy,
    Capability,
    CredentialsFacebook,
    CredentialsGithub,
    CredentialsGoogle,
    CredentialsSlack,
    DeviceId,
    GithubAcademyUser,
    GithubAcademyUserLog,
    GitpodUser,
    Profile,
    ProfileAcademy,
    Role,
    Token,
    UserInvite,
    UserProxy,
    UserSetting,
)
from .tasks import async_set_gitpod_user_expiration

logger = logging.getLogger(__name__)


@admin.display(description="Delete all tokens")
def clean_all_tokens(modeladmin, request, queryset):
    user_ids = queryset.values_list("id", flat=True)
    delete_tokens(users=user_ids, status="all")


@admin.display(description="Delete EXPIRED tokens")
def clean_expired_tokens(modeladmin, request, queryset):
    user_ids = queryset.values_list("id", flat=True)
    delete_tokens(users=user_ids, status="expired")


@admin.display(description="Send reset password link")
def send_reset_password(modeladmin, request, queryset):
    reset_password(users=queryset)


@admin.register(CredentialsGithub)
class CredentialsGithubAdmin(admin.ModelAdmin):
    list_display = ("github_id", "user_id", "email", "token")
    search_fields = ["user__first_name", "user__last_name", "user__email", "email"]
    raw_id_fields = ["user"]


@admin.register(CredentialsGoogle)
class CredentialsGoogleAdmin(admin.ModelAdmin):
    list_display = ("user", "token", "expires_at")
    search_fields = [
        "user__first_name",
        "user__last_name",
        "user__email",
    ]
    raw_id_fields = ["user"]


@admin.register(CredentialsSlack)
class CredentialsSlackAdmin(admin.ModelAdmin):
    list_display = ("user", "app_id", "bot_user_id", "team_id", "team_name")
    search_fields = ["user__first_name", "user__last_name", "user__email"]
    raw_id_fields = ["user"]


@admin.register(CredentialsFacebook)
class CredentialsFacebookAdmin(admin.ModelAdmin):
    list_display = ("facebook_id", "user", "email", "academy", "expires_at")


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("key", "token_type", "expires_at", "user")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_filter = ["token_type"]
    raw_id_fields = ["user"]

    def get_readonly_fields(self, request, obj=None):
        return ["key"]


def accept_selected_users_from_waiting_list(modeladmin, request, queryset: QuerySet[UserInvite]):
    queryset = queryset.exclude(process_status="DONE").order_by("id")
    for x in queryset:
        tasks.async_accept_user_from_waiting_list.delay(x.id)


def accept_all_users_from_waiting_list(modeladmin, request, queryset: QuerySet[UserInvite]):
    queryset = UserInvite.objects.all().exclude(process_status="DONE").order_by("id")
    for x in queryset:
        tasks.async_accept_user_from_waiting_list.delay(x.id)


def validate_email(modeladmin, request, queryset: QuerySet[UserInvite]):
    for x in queryset:
        email_status = marketing_actions.validate_email(x.email, "en")
        x.email_quality = email_status["score"]
        x.email_status = email_status
        x.save()


@admin.register(UserInvite)
class UserInviteAdmin(admin.ModelAdmin):
    search_fields = ["email", "first_name", "last_name", "user__email"]
    raw_id_fields = ["user", "author", "cohort"]
    list_filter = ["academy", "status", "is_email_validated", "process_status", "role", "country"]
    list_display = (
        "email",
        "is_email_validated",
        "first_name",
        "last_name",
        "status",
        "academy",
        "token",
        "created_at",
        "invite_url",
        "country",
    )
    actions = [accept_selected_users_from_waiting_list, accept_all_users_from_waiting_list, validate_email]

    def invite_url(self, obj):
        params = {"callback": "https://4geeks.com"}
        querystr = urllib.parse.urlencode(params)
        url = os.getenv("API_URL") + "/v1/auth/member/invite/" + str(obj.token) + "?" + querystr
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='{url}'>invite url</a>")


@admin.display(description="Clear user password")
def clear_user_password(modeladmin, request, queryset):
    for u in queryset:
        u.set_unusable_password()
        u.save()


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "github_login")
    actions = [clean_all_tokens, clean_expired_tokens, send_reset_password, clear_user_password]

    def get_queryset(self, request):

        self.github_callback = "https://4geeks.com"
        self.github_callback = str(base64.urlsafe_b64encode(self.github_callback.encode("utf-8")), "utf-8")
        return super(UserAdmin, self).get_queryset(request)

    def github_login(self, obj):
        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='/v1/auth/github/?user={obj.id}&url={self.github_callback}'>connect github</a>"
        )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("slug", "name")
    filter_horizontal = ("capabilities",)


@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ("slug", "description")


@admin.register(ProfileAcademy)
class ProfileAcademyAdmin(admin.ModelAdmin):
    list_display = ("user", "stats", "email", "academy", "role", "created_at", "slack", "facebook")
    search_fields = ["user__first_name", "user__last_name", "user__email"]
    list_filter = ["academy__slug", "status", "role__slug"]
    actions = change_field(["ACTIVE", "INVITED"], name="status")
    raw_id_fields = ["user"]

    def get_queryset(self, request):

        self.slack_callback = "https://4geeks.com"
        self.slack_callback = str(base64.urlsafe_b64encode(self.slack_callback.encode("utf-8")), "utf-8")
        return super(ProfileAcademyAdmin, self).get_queryset(request)

    def stats(self, obj):

        colors = {
            "ACTIVE": "bg-success",
            "INVITED": "bg-error",
        }

        return format_html(
            f"<span class='badge {colors[obj.status]}'><a rel='noopener noreferrer' target='_blank' href='/v1/auth/academy/html/invite'>{obj.status}</a></span>"
        )

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
    list_display = ("user", "phone", "github_username", "avatar_url")
    search_fields = ["user__first_name", "user__last_name", "user__email"]
    raw_id_fields = ["user"]
    # actions = [clean_all_tokens, clean_expired_tokens, send_reset_password]


@admin.register(UserSetting)
class UserSettingAdmin(admin.ModelAdmin):
    list_display = ("user", "lang", "main_currency")
    search_fields = ["user__first_name", "user__last_name", "user__email", "user__id"]
    raw_id_fields = ["user"]
    list_filter = ("lang", "main_currency")
    # actions = [clean_all_tokens, clean_expired_tokens, send_reset_password]


@admin.display(description="Generate academy token")
def generate_token(modeladmin, request, queryset):
    academies = queryset.all()
    for a in academies:
        generate_academy_token(a.id)


@admin.display(description="RESET academy token")
def reset_token(modeladmin, request, queryset):
    academies = queryset.all()
    for a in academies:
        generate_academy_token(a.id, force=True)


@admin.register(AcademyProxy)
class AcademyAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "token")
    actions = [generate_token, reset_token]

    def token(self, obj):
        return Token.objects.filter(user__username=obj.slug).first()


@admin.register(DeviceId)
class DeviceIdAdmin(admin.ModelAdmin):
    list_display = ("name", "key")
    search_fields = ["name"]


def recalculate_expiration(modeladmin, request, queryset):
    queryset.update(expires_at=None)
    gp_users = queryset.all()
    for gpu in gp_users:
        gpu = set_gitpod_user_expiration(gpu.id)
        if gpu is None:
            messages.add_message(
                request,
                messages.ERROR,
                f"Error: Gitpod user {gpu.github_username} {gpu.assignee_id} could not be processed",
            )
        else:
            messages.add_message(
                request,
                messages.INFO,
                f"Success: Gitpod user {gpu.github_username} {gpu.assignee_id} was successfully processed",
            )


def async_recalculate_expiration(modeladmin, request, queryset):
    queryset.update(expires_at=None)
    gp_users = queryset.all()
    for gpu in gp_users:
        gpu = async_set_gitpod_user_expiration.delay(gpu.id)


def extend_expiration_2_weeks(modeladmin, request, queryset):
    gp_users = queryset.all()
    for gpu in gp_users:
        gpu.expires_at = gpu.expires_at + datetime.timedelta(days=17)
        gpu.delete_status = gpu.delete_status + ". The expiration date was extend for 2 weeks days"
        gpu.save()
        messages.add_message(request, messages.INFO, "Success: Expiration was successfully extended")


def extend_expiration_4_months(modeladmin, request, queryset):
    gp_users = queryset.all()
    for gpu in gp_users:
        gpu.expires_at = gpu.expires_at + datetime.timedelta(days=120)
        gpu.delete_status = gpu.delete_status + ". The expiration date was extend for 4 months"
        gpu.save()
        messages.add_message(request, messages.INFO, "Success: Expiration was successfully extended")


def mark_as_expired(modeladmin, request, queryset):
    gp_users = queryset.all()
    for gpu in gp_users:
        gpu.expires_at = timezone.now()
        gpu.delete_status = gpu.delete_status + ". The user was expired by force."
        gpu.save()
        messages.add_message(request, messages.INFO, "Success: Gitpod user was expired")


@admin.register(GitpodUser)
class GitpodUserAdmin(admin.ModelAdmin):
    list_display = ("github_username", "expiration", "user", "assignee_id", "expires_at")
    search_fields = ["github_username", "user__email", "user__first_name", "user__last_name", "assignee_id"]
    actions = [
        async_recalculate_expiration,
        recalculate_expiration,
        extend_expiration_2_weeks,
        extend_expiration_4_months,
        mark_as_expired,
    ]

    def expiration(self, obj):
        now = timezone.now()

        if obj.expires_at is None:
            return format_html("<span class='badge bg-warning'>NEVER</span>")
        elif now > obj.expires_at:
            return format_html("<span class='badge bg-error'>EXPIRED</span>")
        elif now > (obj.expires_at + datetime.timedelta(days=3)):
            return format_html(
                f"<span class='badge bg-warning'>In {from_now(obj.expires_at, include_days=True)}</span>"
            )
        else:
            return format_html(
                f"<span class='badge bg-success'>In {from_now(obj.expires_at, include_days=True)}</span>"
            )


def mark_as_pending_delete(modeladmin, request, queryset):
    queryset.all().update(storage_status="PENDING", storage_action="DELETE")


def mark_as_pending_add(modeladmin, request, queryset):
    queryset.all().update(storage_status="PENDING", storage_action="ADD")


def mark_as_ignore(modeladmin, request, queryset):
    queryset.all().update(storage_status="SYNCHED", storage_action="IGNORE")


def clear_storage_log(modeladmin, request, queryset):
    queryset.all().update(storage_log=None)


def look_for_github_credentials(modeladmin, request, queryset):
    users = queryset.all()
    for u in users:
        github = CredentialsGithub.objects.filter(user=u.user).first()
        if github is None:
            u.username = None
        else:
            u.username = github.username
        u.save()


class UsernameFilter(SimpleListFilter):
    title = "username_type"
    parameter_name = "username_type"

    def lookups(self, request, model_admin):
        return [("NONE", "Without username"), ("FULL", "With Username")]

    def queryset(self, request, queryset):
        if self.value() == "NONE":
            return queryset.filter(Q(username__isnull=True) | Q(username=""))
        if self.value() == "FULL":
            return queryset.filter(username__isnull=False).exclude(username="")


@admin.register(GithubAcademyUser)
class GithubAcademyUserAdmin(admin.ModelAdmin):
    list_display = ("id", "academy", "user", "github", "storage_status", "storage_action", "created_at", "updated_at")
    search_fields = ["username", "user__email", "user__first_name", "user__last_name"]
    actions = [
        mark_as_pending_delete,
        mark_as_pending_add,
        mark_as_ignore,
        clear_storage_log,
        look_for_github_credentials,
    ]
    list_filter = ("academy", "storage_status", "storage_action", UsernameFilter)
    raw_id_fields = ["user"]

    def github(self, obj):
        if obj.username is None:
            return "missing github connect"
        else:
            return obj.username


@admin.register(GithubAcademyUserLog)
class GithubAcademyUserLogAdmin(admin.ModelAdmin):
    list_display = (
        "academy_user",
        "academy_name",
        "storage_status",
        "storage_action",
        "created_at",
        "valid_until",
        "updated_at",
    )
    search_fields = [
        "academy_user__username",
        "academy_user__user__email",
        "academy_user__user__first_name",
        "academy_user__user__last_name",
    ]
    # actions = [mark_as_deleted, mark_as_add, mark_as_ignore]
    list_filter = ("academy_user__academy__name", "storage_status", "storage_action")

    def academy_name(self, obj):
        return obj.academy_user.academy.name

    def user_info(self, obj):
        return str(obj.academy_user)
        # if obj.academy_user.username is not None:
        #     info += ' -> ' + obj.academy_user.username


def sync_github_members(modeladmin, request, queryset):
    settings = queryset.all()
    for s in settings:
        try:
            sync_organization_members(s.academy.id)
        except Exception as e:
            logger.error(f"Error while syncing organization members for {s.academy.name}: " + str(e))
            messages.error(request, f"Error while syncing organization members for {s.academy.name}: " + str(e))


def activate_github_sync(modeladmin, request, queryset):
    queryset.update(github_is_sync=True)


def deactivate_github_sync(modeladmin, request, queryset):
    queryset.update(github_is_sync=False)


def clean_errors(modeladmin, request, queryset):
    queryset.update(github_error_log=[])


@admin.register(AcademyAuthSettings)
class AcademyAuthSettingsAdmin(admin.ModelAdmin):
    list_display = ("academy", "github_is_sync", "github_errors", "github_username", "github_owner", "authenticate")
    search_fields = ["academy__slug", "academy__name", "github__username", "academy__id"]
    actions = (clean_errors, activate_github_sync, deactivate_github_sync, sync_github_members)
    raw_id_fields = ["github_owner"]

    def get_queryset(self, request):

        self.github_callback = "https://4geeks.com"
        self.github_callback = str(base64.urlsafe_b64encode(self.github_callback.encode("utf-8")), "utf-8")
        return super(AcademyAuthSettingsAdmin, self).get_queryset(request)

    def github_errors(self, obj):
        if obj.github_error_log is not None and len(obj.github_error_log) > 0:
            return format_html(f"<span class='badge bg-error'>{len(obj.github_error_log)} errors</span>")
        else:
            return format_html("<span class='badge bg-success'>No errors</span>")

    def authenticate(self, obj):
        settings = AcademyAuthSettings.objects.get(id=obj.id)
        if settings.github_owner is None:
            return format_html("no owner")

        scopes = str(base64.urlsafe_b64encode(b"user repo admin:org"), "utf-8")
        return format_html(
            f"<a href='/v1/auth/github?user={obj.github_owner.id}&url={self.github_callback}&scope={scopes}'>connect owner</a>"
        )

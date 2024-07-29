import logging

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.template.defaultfilters import escape
from django.urls import reverse
from django.utils.html import format_html

from breathecode.admissions.admin import CohortAdmin as AdmissionsCohortAdmin
from breathecode.utils import AdminExportCsvMixin

from .actions import send_slack, sync_slack_team_channel
from .models import CohortProxy, Device, HookError, SlackChannel, SlackTeam, SlackUser, SlackUserTeam, UserProxy
from .tasks import async_slack_team_users
from .utils.hook_manager import HookManager

logger = logging.getLogger(__name__)


# Register your models here.
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "registration_id")


@admin.display(description="Import channels from slack")
def sync_channels(modeladmin, request, queryset):
    logger.debug("Bulk sync channels")
    teams = queryset.all()
    for team in teams:
        sync_slack_team_channel(team.id)


@admin.display(description="Import users from slack")
def sync_users(modeladmin, request, queryset):
    logger.debug("Bulk sync channels")
    teams = queryset.all()
    for team in teams:
        async_slack_team_users.delay(team.id)


@admin.register(SlackTeam)
class SlackTeamAdmin(admin.ModelAdmin):
    list_display = ("slack_id", "sync_status", "synqued_at", "academy", "name", "owner", "updated_at")
    actions = [sync_channels, sync_users]


@admin.register(SlackUser)
class SlackUserAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = [
        "slack_id",
        "display_name",
        "real_name",
        "email",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]
    raw_id_fields = ["user"]
    list_display = ("slack_id", "user_link", "display_name", "real_name", "email", "updated_at")
    actions = ["export_as_csv"]

    def user_link(self, obj):
        if obj.user is not None:
            return format_html(
                '<a href="%s">%s</a>' % (reverse("admin:auth_user_change", args=(obj.user.id,)), escape(obj))
            )
        else:
            return "Missing BC user"


@admin.register(SlackUserTeam)
class SlackUserTeamAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = [
        "slack_user__email",
        "slack_user__user__first_name",
        "slack_user__user__last_name",
        "slack_team__id",
        "slack_team__name",
    ]
    raw_id_fields = ["slack_user"]
    list_display = ("slack_user", "sync_status", "breathecode_user", "slack_team", "created_at")
    list_filter = ["slack_team__academy__slug", "slack_team__name", "sync_status"]
    actions = ["export_as_csv"]

    def breathecode_user(self, obj):
        if obj.slack_user.user is not None:
            return format_html(
                '<a href="%s">%s</a>'
                % (reverse("admin:auth_user_change", args=(obj.slack_user.user.id,)), escape(obj.slack_user.user))
            )
        else:
            return "Missing BC user"


@admin.register(SlackChannel)
class SlackChannelAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = ["name", "cohort__name"]
    list_display = ("slack_id", "sync_status", "cohort_link", "name", "synqued_at")
    list_filter = ["sync_status", "team__slack_id", "team__academy__slug"]
    actions = ["export_as_csv"]

    def cohort_link(self, obj):
        if obj.cohort is not None:
            return format_html(
                '<a href="%s">%s</a>' % (reverse("admin:auth_user_change", args=(obj.cohort.id,)), escape(obj))
            )
        else:
            return "No BC cohort"


@admin.display(description="💬 Send slack test notification")
def test_user_notification(modeladmin, request, queryset):

    users = queryset.all()
    for u in users:
        logger.debug(f"Testing slack notification for {u.id}")
        send_slack("test_message", slackuser=u.slackuser, data={"MESSAGE": "Hello World"})


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name")
    actions = [test_user_notification]


@admin.display(description="💬 Send slack test notification")
def test_cohort_notification(modeladmin, request, queryset):

    cohorts = queryset.all()
    for c in cohorts:
        logger.debug(f"Testing slack notification for cohort {c.id}")
        send_slack("test_message", slackchannel=c.slackchannel, data={"MESSAGE": "Hello World"})


@admin.register(CohortProxy)
class CohortAdmin(AdmissionsCohortAdmin):
    list_display = ("id", "slug", "stage", "name", "kickoff_date", "syllabus_version", "schedule")
    actions = [test_cohort_notification]


HookModel = HookManager.get_hook_model()


class HookForm(forms.ModelForm):
    """
    Model form to handle registered events, asuring
    only events declared on HOOK_EVENTS settings
    can be registered.
    """

    class Meta:
        model = HookModel
        exclude = []

    def __init__(self, *args, **kwargs):
        super(HookForm, self).__init__(*args, **kwargs)
        self.fields["event"] = forms.ChoiceField(choices=self.get_admin_events())

    @classmethod
    def get_admin_events(cls):
        return [(x, x) for x in HookManager.HOOK_EVENTS.keys()]


class HookAdmin(admin.ModelAdmin):
    list_display = ["user", "target", "event", "service_id", "total_calls", "last_response_code", "last_call_at"]
    search_fields = ["user__username", "event", "target", "service_id"]
    list_filter = ["event", "last_response_code"]
    raw_id_fields = [
        "user",
    ]
    form = HookForm


admin.site.register(HookModel, HookAdmin)


@admin.register(HookError)
class HookErrorAdmin(admin.ModelAdmin):
    list_display = ["event", "message", "created_at", "updated_at"]
    search_fields = ["message", "event"]
    list_filter = ["event"]

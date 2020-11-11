import logging, csv
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Device, SlackTeam, SlackChannel, SlackUser, UserProxy, CohortProxy, SlackTeam, SlackUserTeam
from .actions import sync_slack_team_users, sync_slack_team_channel, send_slack
from breathecode.admissions.admin import CohortAdmin
from django.utils.html import format_html
from django.template.defaultfilters import escape
from django.urls import reverse
from django.http import HttpResponse

logger = logging.getLogger(__name__)

class ExportCsvMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"

# Register your models here.
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'registration_id')

def sync_channels(modeladmin, request, queryset):
    teams = queryset.all()
    for team in teams:
        sync_slack_team_channel(team.id)
sync_channels.short_description = "Import channels from slack"

def sync_users(modeladmin, request, queryset):
    teams = queryset.all()
    for team in teams:
        sync_slack_team_users(team.id)
sync_users.short_description = "Import users from slack"
@admin.register(SlackTeam)
class SlackTeamAdmin(admin.ModelAdmin):
    list_display = ('slack_id', 'sync_status', 'synqued_at', 'academy', 'name', 'owner', 'updated_at')
    actions = [sync_channels, sync_users]

@admin.register(SlackUser)
class SlackUserAdmin(admin.ModelAdmin, ExportCsvMixin):
    search_fields = ['slack_id','display_name', 'real_name', 'email', 'user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = ["user"]
    list_display = ('slack_id', 'user_link', 'display_name', 'real_name', 'email', 'updated_at')
    actions = ['export_as_csv']
    def user_link(self, obj):
        if obj.user is not None:
            return format_html('<a href="%s">%s</a>' % (reverse("admin:auth_user_change", args=(obj.user.id,)) , escape(obj)))
        else:
            return "Missing BC user"

@admin.register(SlackUserTeam)
class SlackUserTeamAdmin(admin.ModelAdmin, ExportCsvMixin):
    search_fields = ['slack_user__email', 'slack_user__user__first_name', 'slack_user__user__last_name', 'slack_team__id', 'slack_team__name']
    raw_id_fields = ["slack_user"]
    list_display = ('slack_user', 'sync_status', 'breathecode_user', 'slack_team', 'created_at')
    list_filter = ['slack_team__academy__slug', 'slack_team__name', 'sync_status']
    actions = ['export_as_csv']
    def breathecode_user(self, obj):
        if obj.slack_user.user is not None:
            return format_html('<a href="%s">%s</a>' % (reverse("admin:auth_user_change", args=(obj.slack_user.user.id,)) , escape(obj.slack_user.user)))
        else:
            return "Missing BC user"

@admin.register(SlackChannel)
class SlackChannelAdmin(admin.ModelAdmin, ExportCsvMixin):
    search_fields = ['name', 'cohort__name']
    list_display = ('slack_id', 'sync_status', 'cohort_link', 'name', 'synqued_at')
    list_filter = ['sync_status', 'team__slack_id', 'team__academy__slug']
    actions = ['export_as_csv']
    def cohort_link(self, obj):
        if obj.cohort is not None:
            return format_html('<a href="%s">%s</a>' % (reverse("admin:auth_user_change", args=(obj.cohort.id,)) , escape(obj)))
        else:
            return "No BC cohort"


def test_user_notification(modeladmin, request, queryset):

    users = queryset.all()
    for u in users:
        logger.debug(f"Testing slack notification for {u.id}")
        send_slack("test_message", u.slackuser, { "MESSAGE": "Hello World" })
        
test_user_notification.short_description = "💬 Send slack test notification"

@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    actions = [test_user_notification]

def test_cohort_notification(modeladmin, request, queryset):

    cohorts = queryset.all()
    for c in cohorts:
        logger.debug(f"Testing slack notification for cohort {c.id}")
        send_slack("test_message", c.slackchannel, { "MESSAGE": "Hello World" })

test_cohort_notification.short_description = "💬 Send slack test notification"

@admin.register(CohortProxy)
class CohortAdmin(CohortAdmin):
    list_display = ('slug', 'name', 'stage')
    actions = [test_cohort_notification]
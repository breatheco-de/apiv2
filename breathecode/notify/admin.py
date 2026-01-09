import logging

from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.template.defaultfilters import escape
from django.urls import reverse
from django.utils.html import format_html

from breathecode.admissions.admin import CohortAdmin as AdmissionsCohortAdmin
from breathecode.admissions.models import Academy
from breathecode.utils import AdminExportCsvMixin

from .actions import send_slack, sync_slack_team_channel
from .models import (
    AcademyNotifySettings,
    CohortProxy,
    Device,
    HookError,
    Notification,
    SlackChannel,
    SlackTeam,
    SlackUser,
    SlackUserTeam,
    UserProxy,
)
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


class AcademyFilter(SimpleListFilter):
    """Filter HookError by academy through hooks -> user -> profileacademy -> academy."""

    title = "Academy"
    parameter_name = "academy"

    def lookups(self, request, model_admin):
        """Return list of academies that have hooks with errors, plus "No academy" option."""
        from breathecode.authenticate.models import ProfileAcademy

        # Get all academies that have hooks with errors
        # HookError -> hooks (ManyToMany) -> Hook -> user -> ProfileAcademy -> academy
        academies = (
            Academy.objects.filter(
                profileacademy__user__hooks__errors__isnull=False, profileacademy__role__slug="academy_token"
            )
            .distinct()
            .order_by("name")
        )

        # Build list of academy options
        academy_list = [(academy.id, academy.name) for academy in academies]

        # Add "No academy" option for hooks created by non-academy-token users
        # Check if there are any HookError records with hooks from non-academy-token users
        from breathecode.notify.models import Hook, HookError

        academy_token_user_ids = ProfileAcademy.objects.filter(role__slug="academy_token").values_list(
            "user_id", flat=True
        )
        non_academy_hooks = Hook.objects.exclude(user__in=academy_token_user_ids)
        has_non_academy_errors = HookError.objects.filter(hooks__in=non_academy_hooks).exists()

        if has_non_academy_errors:
            academy_list.insert(0, ("no_academy", "No academy"))

        return academy_list

    def queryset(self, request, queryset):
        """Filter queryset by selected academy."""
        if self.value() == "no_academy":
            from breathecode.authenticate.models import ProfileAcademy

            # Get all academy token user IDs
            academy_token_user_ids = ProfileAcademy.objects.filter(role__slug="academy_token").values_list(
                "user_id", flat=True
            )

            # Filter HookError by hooks that belong to users who are NOT academy token users
            from breathecode.notify.models import Hook

            non_academy_hooks = Hook.objects.exclude(user__in=academy_token_user_ids)
            return queryset.filter(hooks__in=non_academy_hooks).distinct()

        elif self.value():
            from breathecode.authenticate.models import ProfileAcademy

            # Get academy token users for this academy
            academy_token_users = ProfileAcademy.objects.filter(
                academy_id=self.value(), role__slug="academy_token"
            ).values_list("user_id", flat=True)

            # Filter HookError by hooks that belong to these users
            return queryset.filter(hooks__user__in=academy_token_users).distinct()

        return queryset


@admin.register(HookError)
class HookErrorAdmin(admin.ModelAdmin):
    list_display = ["event", "message", "created_at", "updated_at"]
    search_fields = ["message", "event"]
    list_filter = ["event", AcademyFilter]

    def get_search_results(self, request, queryset, search_term):
        """
        Override search to support searching by signal name.
        Searches in:
        - Event name (default)
        - Message (default)
        - Signal name (custom - looks up in HOOK_EVENTS_METADATA)
        """
        # Get default search results (searches in event and message fields)
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        if search_term:
            from django.conf import settings
            from breathecode.notify.utils.auto_register_hooks import derive_signal_from_action

            # Get metadata from settings
            metadata = getattr(settings, "HOOK_EVENTS_METADATA", {})

            # Find event names that match the search term in their signal
            matching_events = []
            search_term_lower = search_term.lower()

            for event_name, event_config in metadata.items():
                action = event_config.get("action")
                event_signal = event_config.get("signal")

                # If signal not in config, derive it from action
                if not event_signal and action:
                    event_signal = derive_signal_from_action(action)

                # Check if search term matches signal (partial match)
                if event_signal and search_term_lower in event_signal.lower():
                    matching_events.append(event_name)

            # If we found matching events by signal, combine with existing queryset using OR
            if matching_events:
                # Combine: (default search results) OR (events matching signal)
                signal_queryset = queryset.model.objects.filter(event__in=matching_events)
                queryset = queryset | signal_queryset
                use_distinct = True

        return queryset, use_distinct


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("operation_code", "status", "type", "user", "academy", "done_at", "sent_at", "seen_at")
    search_fields = ("operation_code", "message", "user__username", "user__email", "academy__name")
    list_filter = ("status", "type")
    raw_id_fields = ("user", "academy")


@admin.register(AcademyNotifySettings)
class AcademyNotifySettingsAdmin(admin.ModelAdmin):
    list_display = ("academy", "updated_at")
    search_fields = ("academy__name", "academy__slug")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            None,
            {"fields": ("academy",)},
        ),
        (
            "Template Control",
            {
                "fields": ("disabled_templates",),
                "description": (
                    "Disable specific notification templates for this academy.<br>"
                    "Format: List of template slugs, e.g., <code>[\"welcome_academy\", \"nps_survey\"]</code>"
                ),
            },
        ),
        (
            "Variable Overrides",
            {
                "fields": ("template_variables",),
                "description": (
                    "Override notification variables. Format:<br>"
                    "- Template-specific: <code>\"template.SLUG.VARIABLE\": \"value\"</code><br>"
                    "- Global: <code>\"global.VARIABLE\": \"value\"</code><br>"
                    "Supports interpolation: <code>{{global.VARIABLE}}</code>"
                ),
            },
        ),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

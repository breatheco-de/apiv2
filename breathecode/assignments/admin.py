import logging
import os

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django import forms
from django.db import models

from breathecode.assignments.tasks import async_learnpack_webhook
from breathecode.authenticate.models import Token
from breathecode.services.learnpack import LearnPack
from breathecode.utils.admin.widgets import PrettyJSONWidget

from .actions import sync_student_tasks
from .models import (
    AssignmentTelemetry,
    CohortProxy,
    FinalProject,
    LearnPackWebhook,
    RepositoryDeletionOrder,
    RepositoryWhiteList,
    Task,
    UserAttachment,
    UserProxy,
)
from .tasks import async_calculate_telemetry_indicator

# Register your models here.
logger = logging.getLogger(__name__)


@admin.display(description="Delete and sync Tasks")
def sync_tasks(modeladmin, request, queryset):

    for u in queryset:
        try:
            Task.objects.filter(user_id=u.id).delete()
            sync_student_tasks(u)
        except Exception:
            logger.exception(f"There was a problem syncronizing tassks for student {u.email}")


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name")
    actions = [sync_tasks]


@admin.display(description="Delete AND SYNC Tasks for all students of this cohort")
def sync_cohort_tasks(modeladmin, request, queryset):
    from .actions import sync_cohort_tasks

    for c in queryset:
        try:
            Task.objects.filter(cohort__id=c.id).delete()
            sync_cohort_tasks(c)
        except Exception:
            pass


@admin.display(description="Delete tasks for all students of this cohort")
def delete_cohort_tasks(modeladmin, request, queryset):

    for c in queryset:
        try:
            Task.objects.filter(cohort__id=c.id).delete()
        except Exception:
            pass


@admin.register(CohortProxy)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("id", "slug", "stage", "name", "kickoff_date", "syllabus_version", "schedule")
    actions = [sync_cohort_tasks, delete_cohort_tasks]


@admin.display(description="Mark task status as DONE")
def mark_as_delivered(modeladmin, request, queryset):
    queryset.update(task_status="DONE")


@admin.display(description="Mark revision status as APPROVED")
def mark_as_approved(modeladmin, request, queryset):
    queryset.update(revision_status="APPROVED")


@admin.display(description="Mark revision status as IGNORED")
def mark_as_ignored(modeladmin, request, queryset):
    queryset.update(revision_status="IGNORED")


@admin.display(description="Mark revision status as REJECTED")
def mark_as_rejected(modeladmin, request, queryset):
    queryset.update(revision_status="REJECTED")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    search_fields = ["title", "associated_slug", "user__first_name", "user__last_name", "user__email"]
    list_display = ("title", "task_type", "associated_slug", "task_status", "revision_status", "user", "delivery_url")
    list_filter = ["task_type", "task_status", "revision_status"]
    actions = [mark_as_delivered, mark_as_approved, mark_as_rejected, mark_as_ignored]

    def delivery_url(self, obj):
        token, created = Token.get_or_create(obj.user, token_type="temporal")
        url = os.getenv("API_URL") + f"/v1/assignment/task/{str(obj.id)}/deliver/{token}"
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='{url}'>deliver</a>")


@admin.register(UserAttachment)
class UserAttachmentAdmin(admin.ModelAdmin):
    search_fields = ["slug", "name", "user__first_name", "user__last_name", "user__email"]
    list_display = ("slug", "name", "user", "url", "mime")
    list_filter = ["mime"]


class HasLiveUrlFilter(admin.SimpleListFilter):
    title = "Has Live URL"
    parameter_name = "has_live_url"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(public_url__isnull=False).exclude(public_url="")
        if self.value() == "no":
            return queryset.filter(models.Q(public_url__isnull=True) | models.Q(public_url=""))
        return queryset


class HasGithubUrlFilter(admin.SimpleListFilter):
    title = "Has GitHub URL"
    parameter_name = "has_github_url"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(repo_url__isnull=False).exclude(repo_url="")
        if self.value() == "no":
            return queryset.filter(models.Q(repo_url__isnull=True) | models.Q(repo_url=""))
        return queryset


class HasScreenshotFilter(admin.SimpleListFilter):
    title = "Has Screenshot"
    parameter_name = "has_screenshot"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(screenshot__isnull=False).exclude(screenshot="")
        if self.value() == "no":
            return queryset.filter(models.Q(screenshot__isnull=True) | models.Q(screenshot=""))
        return queryset


@admin.register(FinalProject)
class FinalProjectAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "cohort",
        "project_status",
        "revision_status",
        "visibility_status",
        "github_url",
        "live_url",
        "has_screenshot",
    ]
    search_fields = ("name", "cohort__slug", "repo_url", "members__email")
    filter_horizontal = ["members"]
    raw_id_fields = ["cohort"]
    list_filter = [
        "project_status",
        "revision_status",
        "visibility_status",
        "cohort__academy__slug",
        HasLiveUrlFilter,
        HasGithubUrlFilter,
        HasScreenshotFilter,
    ]
    # actions = [mark_as_delivered, mark_as_approved, mark_as_rejected, mark_as_ignored]

    def github_url(self, obj):
        if obj.repo_url:
            return format_html(f"<a rel='noopener noreferrer' target='_blank' href='{obj.repo_url}'>🔗 GitHub</a>")
        return "-"

    def live_url(self, obj):
        if obj.public_url:
            return format_html(f"<a rel='noopener noreferrer' target='_blank' href='{obj.public_url}'>🌐 Live</a>")
        return "-"

    def has_screenshot(self, obj):
        if obj.screenshot:
            return format_html(f"<a rel='noopener noreferrer' target='_blank' href='{obj.screenshot}'>📸 View</a>")
        return "-"

    github_url.short_description = "GitHub"
    live_url.short_description = "Live URL"
    has_screenshot.short_description = "Screenshot"

    # def delivery_url(self, obj):
    #     token, created = Token.get_or_create(obj.user, token_type='temporal')
    #     url = os.getenv('API_URL') + f'/v1/assignment/task/{str(obj.id)}/deliver/{token}'
    #     return format_html(f"<a rel='noopener noreferrer' target='_blank' href='{url}'>deliver</a>")


def async_process_hook(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for hook in queryset.all().order_by("created_at"):
        async_learnpack_webhook.delay(hook.id)


def process_hook(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for hook in queryset.all().order_by("created_at"):
        client = LearnPack()
        try:
            client.execute_action(hook.id)
        except Exception as e:
            raise e
            pass

    messages.success(request, message="Check each updated status on the webhook list for details")


class EngagementScoreFilter(admin.SimpleListFilter):
    title = "Engagement Score"
    parameter_name = "engagement_score"

    def lookups(self, request, model_admin):
        return (
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
            ("none", "None"),
        )

    def queryset(self, request, queryset):
        if self.value() == "high":
            return queryset.filter(engagement_score__gte=70)
        if self.value() == "medium":
            return queryset.filter(engagement_score__gte=40, engagement_score__lt=70)
        if self.value() == "low":
            return queryset.filter(engagement_score__lt=40)
        if self.value() == "none":
            return queryset.filter(engagement_score__isnull=True)
        return queryset


class FrustrationScoreFilter(admin.SimpleListFilter):
    title = "Frustration Score"
    parameter_name = "frustration_score"

    def lookups(self, request, model_admin):
        return (
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
            ("none", "None"),
        )

    def queryset(self, request, queryset):
        if self.value() == "high":
            return queryset.filter(frustration_score__gte=70)
        if self.value() == "medium":
            return queryset.filter(frustration_score__gte=40, frustration_score__lt=70)
        if self.value() == "low":
            return queryset.filter(frustration_score__lt=40)
        if self.value() == "none":
            return queryset.filter(frustration_score__isnull=True)
        return queryset


@admin.action(description="Calculate Telemetry Indicators")
def calculate_telemetry_indicators(modeladmin, request, queryset):
    for telemetry in queryset:
        async_calculate_telemetry_indicator.delay(telemetry.id)


@admin.register(AssignmentTelemetry)
class AssignmentTelemetryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "asset_slug",
        "user",
        "created_at",
        "engagement_score_display",
        "frustration_score_display",
        "total_time",
        "completion_rate",
    )
    search_fields = ["asset_slug", "user__email", "user__id"]
    raw_id_fields = ["user"]
    list_filter = [EngagementScoreFilter, FrustrationScoreFilter]
    actions = [calculate_telemetry_indicators]

    def engagement_score_display(self, obj):
        if obj.engagement_score is None:
            return "-"
        color = (
            "bg-success" if obj.engagement_score >= 70 else "bg-warning" if obj.engagement_score >= 40 else "bg-error"
        )
        emoji = "🥳" if obj.engagement_score >= 70 else "😐" if obj.engagement_score >= 40 else "😴"
        return format_html(
            f"<span class='badge {color}'>{emoji} {obj.engagement_score}% v{obj.metrics_algo_version}</span>"
        )

    def frustration_score_display(self, obj):
        if obj.frustration_score is None:
            return "-"
        color = (
            "bg-error" if obj.frustration_score >= 70 else "bg-warning" if obj.frustration_score >= 40 else "bg-success"
        )
        emoji = "🤬" if obj.frustration_score >= 70 else "😤" if obj.frustration_score >= 40 else "😍"
        return format_html(
            f"<span class='badge {color}'>{emoji} {obj.frustration_score}% v{obj.metrics_algo_version}</span>"
        )

    engagement_score_display.short_description = "Engagement Score"
    frustration_score_display.short_description = "Frustration Score"


class LearnPackWebhookForm(forms.ModelForm):
    class Meta:
        model = LearnPackWebhook
        fields = "__all__"
        widgets = {
            "payload": PrettyJSONWidget(attrs={"help_text": "Edit the JSON payload here"}),
        }


@admin.register(LearnPackWebhook)
class LearnPackWebhookAdmin(admin.ModelAdmin):
    form = LearnPackWebhookForm
    list_display = ("id", "event", "status", "student", "created_at")
    search_fields = ["telemetry__asset_slug", "telemetry__user__email"]
    list_filter = ["status", "event"]
    raw_id_fields = ["student", "telemetry"]
    actions = [process_hook, async_process_hook]

    def current_status(self, obj):
        colors = {
            "DONE": "bg-success",
            "ERROR": "bg-error",
            "PENDING": "bg-warning",
            "IGNORED": "",
            "webhook": "bg-warning",
            None: "bg-warning",
        }

        def from_status(s):
            if s in colors:
                return colors[s]
            return ""

        return format_html(
            f"<div><span class='badge {from_status(obj.status)}'>{obj.status}</span></div><small>{obj.status_text}</small>"
        )


@admin.register(RepositoryDeletionOrder)
class RepositoryDeletionOrderAdmin(admin.ModelAdmin):
    list_display = ("provider", "status", "repository_user", "repository_name")
    search_fields = ["repository_user", "repository_name"]
    list_filter = ["provider", "status"]
    raw_id_fields = ["user"]


@admin.register(RepositoryWhiteList)
class RepositoryWhiteListAdmin(admin.ModelAdmin):
    list_display = ("provider", "repository_user", "repository_name")
    search_fields = ["repository_user", "repository_name"]
    list_filter = ["provider"]

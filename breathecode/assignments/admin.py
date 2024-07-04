import logging
import os

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from breathecode.assignments.tasks import async_learnpack_webhook
from breathecode.authenticate.models import Token
from breathecode.services.learnpack import LearnPack

from .actions import sync_student_tasks
from .models import AssignmentTelemetry, CohortProxy, FinalProject, LearnPackWebhook, Task, UserAttachment, UserProxy

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


@admin.register(FinalProject)
class FinalProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "cohort", "project_status", "revision_status", "visibility_status"]
    search_fields = ("name", "cohort__slug", "repo_url", "members__email")
    filter_horizontal = ["members"]
    raw_id_fields = ["cohort"]
    list_filter = ["project_status", "revision_status", "visibility_status", "cohort__academy__slug"]
    # actions = [mark_as_delivered, mark_as_approved, mark_as_rejected, mark_as_ignored]

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
        print(f"Procesing hook: {hook.id}")
        client = LearnPack()
        try:
            client.execute_action(hook.id)
        except Exception as e:
            raise e
            pass

    messages.success(request, message="Check each updated status on the webhook list for details")


@admin.register(AssignmentTelemetry)
class AssignmentTelemetryAdmin(admin.ModelAdmin):
    list_display = ("id", "asset_slug", "user", "created_at")
    search_fields = ["asset_slug", "user__email", "user__id"]
    raw_id_fields = ["user"]


@admin.register(LearnPackWebhook)
class LearnPackWebhookAdmin(admin.ModelAdmin):
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
            "webhook": "bg-warning",
            None: "bg-warning",
        }

        def from_status(s):
            if s in colors:
                return colors[s]
            return ""

        return format_html(f"<div><span class='badge'>{obj.status}</span></div><small>{obj.status_text}</small>")

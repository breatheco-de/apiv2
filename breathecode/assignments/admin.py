import logging, os
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from breathecode.admissions.admin import CohortAdmin
from django.contrib.auth.models import User
from breathecode.authenticate.models import Token
from django.utils.html import format_html
from .models import Task, UserProxy, CohortProxy
from .actions import sync_student_tasks, sync_cohort_tasks
# Register your models here.
logger = logging.getLogger(__name__)


def sync_tasks(modeladmin, request, queryset):

    for u in queryset:
        try:
            Task.objects.filter(user_id=u.id).delete()
            sync_student_tasks(u)
        except Exception as e:
            logger.exception(f'There was a problem syncronizing tassks for student {u.email}')


sync_tasks.short_description = 'Delete and sync Tasks'


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    actions = [sync_tasks]


def sync_cohort_tasks(modeladmin, request, queryset):

    for c in queryset:
        try:
            Task.objects.filter(cohort__id=c.id).delete()
            sync_cohort_tasks(c)
        except Exception as e:
            pass


sync_cohort_tasks.short_description = 'Delete AND SYNC Tasks for all students of this cohort'


def delete_cohort_tasks(modeladmin, request, queryset):

    for c in queryset:
        try:
            Task.objects.filter(cohort__id=c.id).delete()
        except Exception as e:
            pass


delete_cohort_tasks.short_description = 'Delete tasks for all students of this cohort'


@admin.register(CohortProxy)
class CohortAdmin(CohortAdmin):
    list_display = ('id', 'slug', 'stage', 'name', 'kickoff_date', 'syllabus_version', 'schedule')
    actions = [sync_cohort_tasks, delete_cohort_tasks]


def mark_as_delivered(modeladmin, request, queryset):
    queryset.update(task_status='DONE')


mark_as_delivered.short_description = 'Mark task status as DONE'


def mark_as_approved(modeladmin, request, queryset):
    queryset.update(revision_status='APPROVED')


mark_as_approved.short_description = 'Mark revision status as APPROVED'


def mark_as_ignored(modeladmin, request, queryset):
    queryset.update(revision_status='IGNORED')


mark_as_ignored.short_description = 'Mark revision status as IGNORED'


def mark_as_rejected(modeladmin, request, queryset):
    queryset.update(revision_status='REJECTED')


mark_as_rejected.short_description = 'Mark revision status as REJECTED'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    search_fields = ['title', 'associated_slug', 'user__first_name', 'user__last_name', 'user__email']
    list_display = ('title', 'task_type', 'associated_slug', 'task_status', 'revision_status', 'user',
                    'delivery_url')
    list_filter = ['task_type', 'task_status', 'revision_status']
    actions = [mark_as_delivered, mark_as_approved, mark_as_rejected, mark_as_ignored]

    def delivery_url(self, obj):
        token, created = Token.get_or_create(obj.user, token_type='temporal')
        url = os.getenv('API_URL') + f'/v1/assignment/task/{str(obj.id)}/deliver/{token}'
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='{url}'>deliver</a>")

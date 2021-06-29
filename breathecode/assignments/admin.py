import logging
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from breathecode.admissions.admin import CohortAdmin
from django.contrib.auth.models import User
from django.contrib import messages
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
            logger.exception(
                f"There was a problem syncronizing tassks for student {u.email}"
            )


sync_tasks.short_description = "Delete and sync Tasks"


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


sync_cohort_tasks.short_description = "Delete AND SYNC Tasks for all students of this cohort"


def delete_cohort_tasks(modeladmin, request, queryset):

    for c in queryset:
        try:
            Task.objects.filter(cohort__id=c.id).delete()
        except Exception as e:
            pass


delete_cohort_tasks.short_description = "Delete tasks for all students of this cohort"


@admin.register(CohortProxy)
class CohortAdmin(CohortAdmin):
    list_display = ('slug', 'name', 'stage')
    actions = [sync_cohort_tasks, delete_cohort_tasks]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    search_fields = [
        'title', 'associated_slug', 'user__first_name', 'user__last_name',
        'user__email'
    ]
    list_display = ('title', 'task_type', 'associated_slug', 'task_status',
                    'revision_status', 'user')
    list_filter = ['task_type', 'task_status', 'revision_status']

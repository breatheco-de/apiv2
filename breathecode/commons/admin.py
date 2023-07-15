from django.contrib import admin
from .models import TaskManager
from breathecode.commons import tasks


def cancel(modeladmin, request, queryset):
    for x in queryset.all():
        tasks.mark_task_as_cancelled.delay(x.id)


def reverse(modeladmin, request, queryset):
    for x in queryset.all():
        tasks.mark_task_as_reversed.delay(x.id)


def force_reverse(modeladmin, request, queryset):
    for x in queryset.all():
        tasks.mark_task_as_reversed.delay(x.id, force=True)


def pause(modeladmin, request, queryset):
    for x in queryset.all():
        tasks.mark_task_as_paused.delay(x.id)


def resume(modeladmin, request, queryset):
    for x in queryset.all():
        tasks.mark_task_as_pending.delay(x.id)


@admin.register(TaskManager)
class TaskManagerAdmin(admin.ModelAdmin):
    list_display = [
        'task_module', 'task_name', 'reverse_module', 'reverse_name', 'status', 'killed', 'last_run',
        'current_page', 'total_pages'
    ]
    search_fields = ['task_module', 'task_name', 'reverse_module', 'reverse_name']
    list_filter = ['status', 'killed', 'task_module']
    actions = [pause, resume, cancel, reverse, force_reverse]

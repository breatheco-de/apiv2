from django.contrib import admin

from breathecode.commons import tasks

from .models import TaskManager, TaskWatcher


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
        'task_module', 'task_name', 'reverse_module', 'reverse_name', 'status', 'get_duration', 'last_run',
        'current_page', 'total_pages', 'killed'
    ]
    search_fields = ['task_module', 'task_name', 'reverse_module', 'reverse_name']
    list_filter = ['status', 'killed', 'task_module']
    actions = [pause, resume, cancel, reverse, force_reverse]

    @admin.display(description='Duration (ms)')
    def get_duration(self, obj):
        if obj.started_at is None:
            return 'No started'

        duration = obj.updated_at - obj.started_at
        # Calculating duration in milliseconds
        duration_ms = duration.total_seconds() * 1000
        return f'{int(duration_ms)} ms'


@admin.register(TaskWatcher)
class TaskWatcherAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'on_error', 'on_success', 'watch_progress']
    search_fields = ['email', 'user__email', 'user__username', 'user__first_name', 'user__last_name']
    list_filter = ['on_error', 'on_success', 'watch_progress']
    raw_id_fields = ['user']

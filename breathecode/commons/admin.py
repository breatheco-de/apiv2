from task_manager.django.admin import TaskManagerAdmin as TMA
from breathecode.activity import tasks as activity_tasks


def upload(modeladmin, request, queryset):
    for x in queryset.all():

        activity_tasks.upload_activities.delay(task_manager_id=x.id)


TMA.actions = TMA.actions + [upload]

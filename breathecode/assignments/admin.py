from django.contrib import admin
from .models import Task

# Register your models here.

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    search_fields = ['title', 'associated_slug', 'user__first_name', 'user__last_name', 'user__email']
    list_display = ('title', 'task_type', 'associated_slug', 'user')
    list_filter = ['task_type', 'task_status', 'revision_status']
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from .models import Answer, UserProxy
from .actions import send_survey

def send_bulk_survey(modeladmin, request, queryset):
    user = queryset.all()
    for u in user:
        send_survey(u)

send_bulk_survey.short_description = "Send Survey"

@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    actions = [send_bulk_survey]
    
# Register your models here.
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'score', 'comment', 'created_at')
    # def entity(self, object):
    #     return f"{object.entity_slug} (id:{str(object.entity_id)})"
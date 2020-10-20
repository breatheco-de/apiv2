import logging
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from breathecode.admissions.admin import CohortAdmin

from .models import Answer, UserProxy, CohortProxy
from .actions import send_survey
from .tasks import send_cohort_survey

logger = logging.getLogger(__name__)

def send_bulk_survey(modeladmin, request, queryset):
    user = queryset.all()
    for u in user:
        send_survey(u)
send_bulk_survey.short_description = "Send General NPS Survey"

@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    actions = [send_bulk_survey]

def send_cohort_bulk_survey(modeladmin, request, queryset):
    logger.debug(f"Send bulk survey called")

    cohort_ids = queryset.values_list('id', flat=True)
    for _id in cohort_ids:
        logger.debug(f"Sending survey to cohort {_id}")
        send_cohort_survey.delay(_id)

    logger.info(f"All surveys scheduled to send")

send_bulk_survey.short_description = "Send NPS Survey to all students"

@admin.register(CohortProxy)
class CohortAdmin(CohortAdmin):
    actions = [send_cohort_bulk_survey]
    
# Register your models here.
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('status', 'user', 'score', 'comment','created_at')
    # def entity(self, object):
    #     return f"{object.entity_slug} (id:{str(object.entity_id)})"
import logging
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from breathecode.admissions.admin import CohortAdmin
from .models import Answer, UserProxy, CohortProxy
from .actions import send_question
from .tasks import send_cohort_survey

logger = logging.getLogger(__name__)

def send_bulk_survey(modeladmin, request, queryset):
    user = queryset.all()
    try:
        for u in user:
            send_question(u)
        messages.success(request, message="Survey was successfully sent")
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))
        
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
send_cohort_bulk_survey.short_description = "Send NPS Survey to all cohort students"

@admin.register(CohortProxy)
class CohortAdmin(CohortAdmin):
    actions = [send_cohort_bulk_survey]
    
# Register your models here.
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'cohort__slug']
    list_display = ('status', 'user', 'score', 'comment', 'opened_at', 'cohort', 'created_at')
    list_filter = ['status', 'score', 'academy__slug', 'cohort__slug']
    # def entity(self, object):
    #     return f"{object.entity_slug} (id:{str(object.entity_id)})"
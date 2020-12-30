import logging
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from breathecode.admissions.admin import CohortAdmin, CohortUserAdmin
from .models import Answer, UserProxy, CohortProxy, CohortUserProxy
from .actions import send_survey
from .tasks import send_cohort_survey

logger = logging.getLogger(__name__)


def send_bulk_survey(modeladmin, request, queryset):
    # mocking tools are poor to apply it
    from django.contrib import messages

    user = queryset.all()
    errors = {}

    for u in user:
        try:
            send_survey(u)
        except Exception as e:
            error = str(e)

            if error in errors:
                errors[error] += 1
            else:
                errors[error] = 1

            logger.fatal(error)
            
    if errors:
        message = ' - '.join([f'{error} ({errors[error]})' for error in errors.keys()])
        messages.error(request, message=message)
    else:
        messages.success(request, message="Survey was successfully sent")    
send_bulk_survey.short_description = "Send General NPS Survey"


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    actions = [send_bulk_survey]


def send_bulk_cohort_user_survey(modeladmin, request, queryset):
    from django.contrib import messages

    cus = queryset.all()
    errors = {}

    for cu in cus:
        try:
            send_survey(cu.user, cu.cohort)
        except Exception as e:
            error = str(e)

            if error in errors:
                errors[error] += 1
            else:
                errors[error] = 1

            logger.fatal(error)

    if errors:
        message = ' - '.join([f'{error} ({errors[error]})' for error in errors.keys()])
        messages.error(request, message=message)
    else:
        messages.success(request, message="Survey was successfully sent")
send_bulk_cohort_user_survey.short_description = "Send General NPS Survey"


@admin.register(CohortUserProxy)
class CohortUserAdmin(CohortUserAdmin):
    actions = [send_bulk_cohort_user_survey]


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
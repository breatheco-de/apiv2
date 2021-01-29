import logging
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from breathecode.admissions.admin import CohortAdmin, CohortUserAdmin
from .models import Answer, UserProxy, CohortProxy, CohortUserProxy, Survey
from .actions import send_question, send_survey_group
from .tasks import send_cohort_survey
from django.utils.html import format_html

logger = logging.getLogger(__name__)


def send_bulk_survey(modeladmin, request, queryset):
    # mocking tools are poor to apply it
    from django.contrib import messages

    user = queryset.all()
    errors = {}

    for u in user:
        try:
            send_question(u)
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
            send_question(cu.user, cu.cohort)
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
    actions = [send_bulk_cohort_user_survey, ]


def send_cohort_bulk_survey(modeladmin, request, queryset):
    logger.debug(f"Send bulk survey called")

    cohort_ids = queryset.values_list('id', flat=True)
    for _id in cohort_ids:
        logger.debug(f"Sending survey to cohort {_id}")
        send_cohort_survey.delay(_id)

    logger.info(f"All surveys scheduled to send")
send_cohort_bulk_survey.short_description = "Send INDIVIDUAL small survey to all cohort students"


@admin.register(CohortProxy)
class CohortAdmin(CohortAdmin):
    actions = [send_cohort_bulk_survey]


# Register your models here.
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('status', 'user', 'score', 'comment', 'opened_at', 'cohort', 'mentor', 'created_at', 'answer_url')
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'cohort__slug']
    list_filter = ['status', 'score', 'academy__slug', 'cohort__slug']
    def answer_url(self,obj):
        url = "https://nps.breatheco.de/" + str(obj.id)
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='{url}'>open answer</a>")
    # def entity(self, object):
    #     return f"{object.entity_slug} (id:{str(object.entity_id)})"

def send_big_cohort_bulk_survey(modeladmin, request, queryset):
    logger.debug(f"send_big_cohort_bulk_survey called")

    # cohort_ids = queryset.values_list('id', flat=True)
    surveys = queryset.all()
    success = True
    for s in surveys:
        logger.debug(f"Sending survey {s.id}")
        # send_cohort_survey.delay(_id)
        try:
            send_survey_group(survey=s)
        except Exception as e:
            success = False
            logger.fatal(str(e))
    if not success:
        messages.error(request, message="Some surveys have not been sent")

    logger.info(f"All surveys scheduled to send for cohorts")

send_big_cohort_bulk_survey.short_description = "Send GENERAL BIG Survey to all cohort students"
@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('cohort', 'status', 'duration', 'created_at', 'survey_url')
    search_fields = ['cohort__slug', 'cohort__academy__slug', 'cohort__name', 'cohort__academy__name']
    list_filter = ['status', 'cohort__academy__slug']
    actions = [send_big_cohort_bulk_survey]
    def survey_url(self,obj):
        url = "https://nps.breatheco.de/survey/" + str(obj.id)
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='{url}'>open survey</a>")

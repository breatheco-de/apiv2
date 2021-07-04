import logging
import json
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from breathecode.admissions.admin import CohortAdmin, CohortUserAdmin
from .models import Answer, UserProxy, CohortProxy, CohortUserProxy, Survey
from .actions import send_question, send_survey_group
from django.utils.html import format_html
from breathecode.utils import AdminExportCsvMixin

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
        message = ' - '.join(
            [f'{error} ({errors[error]})' for error in errors.keys()])
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
        message = ' - '.join(
            [f'{error} ({errors[error]})' for error in errors.keys()])
        messages.error(request, message=message)
    else:
        messages.success(request, message="Survey was successfully sent")


send_bulk_cohort_user_survey.short_description = "Send General NPS Survey"


@admin.register(CohortUserProxy)
class CohortUserAdmin(CohortUserAdmin):
    actions = [
        send_bulk_cohort_user_survey,
    ]


@admin.register(CohortProxy)
class CohortAdmin(CohortAdmin):
    pass


def add_academy_to_answer(modeladmin, request, queryset):

    for answer in queryset:
        try:
            answer.academy = answer.cohort.academy
        except:
            answer.academy = answer.academy
        else:
            pass
        answer.save()


add_academy_to_answer.short_description = "Add academy to answer"
# Register your models here.


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    list_display = ('status', 'user', 'academy', 'cohort', 'mentor', 'score',
                    'comment', 'opened_at', 'created_at', 'answer_url')
    search_fields = [
        'user__first_name', 'user__last_name', 'user__email', 'cohort__slug'
    ]
    list_filter = ['status', 'score', 'academy__slug', 'cohort__slug']
    actions = ["export_as_csv", add_academy_to_answer]
    raw_id_fields = ["user", "cohort", "mentor"]

    def answer_url(self, obj):
        url = "https://nps.breatheco.de/" + str(obj.id)
        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='{url}'>open answer</a>"
        )

    # def entity(self, object):
    #     return f"{object.entity_slug} (id:{str(object.entity_id)})"


def send_big_cohort_bulk_survey(modeladmin, request, queryset):
    logger.debug(f"send_big_cohort_bulk_survey called")

    # cohort_ids = queryset.values_list('id', flat=True)
    surveys = queryset.all()
    for s in surveys:
        logger.debug(f"Sending survey {s.id}")

        try:
            result = send_survey_group(survey=s)
            s.status_json = json.dumps(result)
            if len(result["success"]) == 0:
                s.status = 'FATAL'
            elif len(result["error"]) > 0:
                s.status = 'PARTIAL'
            else:
                s.status = 'SENT'
        except Exception as e:
            s.status = 'FATAL'
            logger.fatal(str(e))
    if s.status != 'SENT':
        messages.error(request, message="Some surveys have not been sent")
    s.save()

    logger.info(f"All surveys scheduled to send for cohorts")


send_big_cohort_bulk_survey.short_description = "Send GENERAL BIG Survey to all cohort students"


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('cohort', 'status', 'duration', 'created_at', 'survey_url')
    search_fields = [
        'cohort__slug', 'cohort__academy__slug', 'cohort__name',
        'cohort__academy__name'
    ]
    list_filter = ['status', 'cohort__academy__slug']
    raw_id_fields = ["cohort"]
    actions = [send_big_cohort_bulk_survey]

    def survey_url(self, obj):
        url = "https://nps.breatheco.de/survey/" + str(obj.id)
        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='{url}'>open survey</a>"
        )

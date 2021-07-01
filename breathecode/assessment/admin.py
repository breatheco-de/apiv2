import logging
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from breathecode.admissions.admin import CohortAdmin
from .models import Assessment, UserAssessment, UserProxy, Question, Option, Answer
from .actions import send_assestment
# from .tasks import send_cohort_survey

logger = logging.getLogger(__name__)


def send_bulk_assesment(modeladmin, request, queryset):
    user = queryset.all()
    try:
        for u in user:
            send_assestment(u)
        messages.success(request, message="Assessment was successfully sent")
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


send_bulk_assesment.short_description = "Send General Assessment"


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    actions = [send_bulk_assesment]


# Register your models here.
@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    search_fields = [
        'title', 'user__first_name', 'user__last_name', 'user__email',
        'academy__slug'
    ]
    list_display = ('title', 'academy', 'comment', 'created_at')
    list_filter = ['private', 'academy__slug']
    # def entity(self, object):
    #     return f"{object.entity_slug} (id:{str(object.entity_id)})"


# Register your models here.
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    search_fields = ['title', 'assessment__title']
    list_display = ['title', 'lang', 'assessment', 'question_type']
    list_filter = ['lang', 'question_type']


# Register your models here.
@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    search_fields = ['title', 'question__assessment__title']
    list_display = ['title', 'lang', 'score', 'question']
    list_filter = ['lang']


# Register your models here.
@admin.register(UserAssessment)
class UserAssessmentAdmin(admin.ModelAdmin):
    search_fields = ['title', 'question__assessment__title']
    list_display = [
        'title', 'status', 'lang', 'owner', 'total_score', 'assessment'
    ]
    list_filter = ['lang']

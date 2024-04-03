import logging
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from .models import (Assessment, UserAssessment, UserProxy, Question, Option, AssessmentThreshold, Answer)
from .actions import send_assestment

logger = logging.getLogger(__name__)


@admin.display(description='Send General Assessment')
def send_bulk_assesment(modeladmin, request, queryset):
    user = queryset.all()
    try:
        for u in user:
            send_assestment(u)
        messages.success(request, message='Assessment was successfully sent')
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    actions = [send_bulk_assesment]


# Register your models here.
@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    search_fields = ['title', 'slug', 'academy__slug']
    list_display = ('slug', 'lang', 'title', 'academy', 'created_at')
    list_filter = ['private', 'academy__slug']
    # def entity(self, object):
    #     return f"{object.entity_slug} (id:{str(object.entity_id)})"


# Register your models here.
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    search_fields = ['title', 'assessment__title']
    list_display = ['title', 'is_deleted', 'position', 'lang', 'assessment', 'question_type']
    list_filter = ['lang', 'question_type', 'is_deleted']


# Register your models here.
@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    search_fields = ['title', 'question__assessment__title']
    list_display = ['title', 'is_deleted', 'position', 'lang', 'score', 'question']
    list_filter = ['lang', 'is_deleted']


# Register your models here.
@admin.register(UserAssessment)
class UserAssessmentAdmin(admin.ModelAdmin):
    search_fields = ['title', 'question__assessment__title']
    list_display = ['title', 'status', 'lang', 'owner', 'total_score', 'assessment']
    list_filter = ['lang']


@admin.register(AssessmentThreshold)
class UserAssessmentThresholdAdmin(admin.ModelAdmin):
    search_fields = ['assessment__slug', 'assessment__title']
    list_display = ['id', 'score_threshold', 'assessment']
    list_filter = ['assessment__slug']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    search_fields = ['user_assesment__owner', 'user_assesment__title']
    list_display = ['id', 'question', 'option', 'value']
    list_filter = ['user_assesment__assessment__slug']

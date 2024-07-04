import logging
import re

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from breathecode.utils.admin import change_field

from .actions import send_assestment
from .models import (
    Answer,
    Assessment,
    AssessmentLayout,
    AssessmentThreshold,
    Option,
    Question,
    UserAssessment,
    UserProxy,
)

logger = logging.getLogger(__name__)


@admin.display(description="Send General Assessment")
def send_bulk_assesment(modeladmin, request, queryset):
    user = queryset.all()
    try:
        for u in user:
            send_assestment(u)
        messages.success(request, message="Assessment was successfully sent")
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name")


# Register your models here.
@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    search_fields = ["title", "slug", "academy__slug"]
    list_display = ("slug", "lang", "title", "academy", "created_at")
    list_filter = ["private", "academy__slug"]
    # def entity(self, object):
    #     return f"{object.entity_slug} (id:{str(object.entity_id)})"


# Register your models here.
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    search_fields = ["title", "assessment__title"]
    list_display = ["title", "is_deleted", "position", "lang", "assessment", "question_type"]
    list_filter = ["lang", "question_type", "is_deleted"]


# Register your models here.
@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    search_fields = ["title", "question__assessment__title"]
    list_display = ["id", "title", "is_deleted", "position", "lang", "score", "question"]
    list_filter = ["lang", "is_deleted"]


def change_status_answered(modeladmin, request, queryset):
    items = queryset.all()
    for i in items:
        i.status = "ANSWERED"
        i.save()


@admin.register(UserAssessment)
class UserAssessmentAdmin(admin.ModelAdmin):
    search_fields = ["title", "question__assessment__title"]
    readonly_fields = ("token",)
    list_display = ["id", "title", "current_status", "lang", "owner", "total_score", "assessment", "academy"]
    list_filter = ["lang", "status", "academy"]
    actions = [change_status_answered] + change_field(["DRAFT", "SENT", "ERROR", "EXPIRED"], name="status")

    def current_status(self, obj):
        colors = {
            "DRAFT": "bg-secondary",
            "SENT": "bg-warning",
            "ANSWERED": "bg-success",
            "ERROR": "bg-error",
            "EXPIRED": "bg-warning",
            None: "bg-error",
        }

        def from_status(s):
            if s in colors:
                return colors[s]
            return ""

        status = "No status"
        if obj.status_text is not None:
            status = re.sub(r"[^\w\._\-]", " ", obj.status_text)
        return format_html(
            f"""<table style='max-width: 200px;'>
        <td><span class='badge {from_status(obj.status)}'>{obj.status}</span></td>
        <tr><td>{status}</td></tr>
        </table>"""
        )


@admin.register(AssessmentThreshold)
class UserAssessmentThresholdAdmin(admin.ModelAdmin):
    search_fields = ["assessment__slug", "assessment__title", "tags"]
    list_display = ["id", "title", "score_threshold", "assessment", "tags"]
    list_filter = ["assessment__slug"]
    actions = []


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    search_fields = ["user_assessment__owner", "user_assessment__title"]
    list_display = ["id", "user_assessment", "question", "option", "value"]
    list_filter = ["user_assessment__assessment__slug"]


@admin.register(AssessmentLayout)
class AssessmentLayoutAdmin(admin.ModelAdmin):
    search_fields = ["slug"]
    list_display = ["id", "slug", "academy"]
    list_filter = ["academy"]

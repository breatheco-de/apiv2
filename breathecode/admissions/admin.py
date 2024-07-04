import os
import pytz
import json
import re
import requests
import base64
from django.contrib import admin
from django import forms
from django.utils import timezone
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from breathecode.utils.datetime_integer import from_now
from breathecode.utils import getLogger
from django.db.models import QuerySet
from breathecode.activity.tasks import get_attendancy_log

from breathecode.marketing.tasks import add_cohort_slug_as_acp_tag, add_cohort_task_to_student
from .models import (
    Academy,
    SyllabusSchedule,
    Cohort,
    CohortUser,
    Country,
    City,
    SyllabusVersion,
    UserAdmissions,
    Syllabus,
    CohortTimeSlot,
    SyllabusScheduleTimeSlot,
)
from .actions import ImportCohortTimeSlots, test_syllabus
from .tasks import async_test_syllabus
from breathecode.assignments.actions import sync_student_tasks
from random import choice
from django.db.models import Q

logger = getLogger(__name__)

# Register your models here.
admin.site.site_header = "4Geeks"
admin.site.index_title = "Administration Portal"
admin.site.site_title = "Administration Portal"

timezones = [(x, x) for x in pytz.common_timezones]


@admin.register(UserAdmissions)
class UserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff")


class AcademyForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(AcademyForm, self).__init__(*args, **kwargs)
        self.fields["timezone"] = forms.ChoiceField(choices=timezones)


@admin.display(description="Mark as available as SAAS")
def mark_as_available_as_saas(modeladmin, request, queryset):
    queryset.update(available_as_saas=True)


@admin.display(description="Mark as unavailable as SAAS")
def mark_as_unavailable_as_saas(modeladmin, request, queryset):
    queryset.update(available_as_saas=False)


@admin.register(Academy)
class AcademyAdmin(admin.ModelAdmin):
    form = AcademyForm
    list_display = ("id", "slug", "name", "city")
    actions = [mark_as_available_as_saas, mark_as_unavailable_as_saas]


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("code", "name")


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "country")


@admin.display(description="Make him/her an ASSISTANT")
def make_assistant(modeladmin, request, queryset):
    cohort_users = queryset.all()
    for cu in cohort_users:
        cu.role = "ASSISTANT"
        cu.save()


@admin.display(description="Make him/her a TEACHER")
def make_teacher(modeladmin, request, queryset):
    cohort_users = queryset.all()
    for cu in cohort_users:
        cu.role = "TEACHER"
        cu.save()


@admin.display(description="Make him/her a STUDENT")
def make_student(modeladmin, request, queryset):
    cohort_users = queryset.all()
    for cu in cohort_users:
        cu.role = "STUDENT"
        cu.save()


@admin.display(description="Educational_status = ACTIVE")
def make_edu_stat_active(modeladmin, request, queryset):
    cohort_users = queryset.all()
    for cu in cohort_users:
        cu.educational_status = "ACTIVE"
        cu.save()


@admin.display(description="Educational_status = GRADUATED")
def make_edu_stat_graduate(modeladmin, request, queryset):
    cohort_users = queryset.all()
    for cu in cohort_users:
        cu.educational_status = "GRADUATED"
        cu.save()


@admin.display(description="Add student tag to active campaign")
def add_student_tag_to_active_campaign(modeladmin, request, queryset):
    cohort_users = queryset.all()
    for v in cohort_users:
        add_cohort_task_to_student.delay(v.user.id, v.cohort.id, v.cohort.academy.id)


@admin.register(CohortUser)
class CohortUserAdmin(admin.ModelAdmin):
    search_fields = ["user__email", "user__first_name", "user__last_name", "cohort__name", "cohort__slug"]
    list_display = ("get_student", "cohort", "role", "educational_status", "finantial_status", "created_at")
    list_filter = ["role", "educational_status", "finantial_status"]
    raw_id_fields = ["user", "cohort"]
    actions = [make_assistant, make_teacher, make_student, make_edu_stat_active, add_student_tag_to_active_campaign]

    def get_student(self, obj):
        return obj.user.first_name + " " + obj.user.last_name + "(" + obj.user.email + ")"


@admin.display(description="Sync Tasks")
def sync_tasks(modeladmin, request, queryset):
    cohort_ids = queryset.values_list("id", flat=True)
    cohort_user = CohortUser.objects.filter(cohort__id__in=[cohort_ids])
    for cu in cohort_user:
        sync_student_tasks(cu.user)


@admin.display(description="Mark as ENDED")
def mark_as_ended(modeladmin, request, queryset):
    queryset.update(stage="ENDED")


@admin.display(description="Mark as STARTED")
def mark_as_started(modeladmin, request, queryset):
    queryset.update(stage="STARTED")


@admin.display(description="Mark as INACTIVE")
def mark_as_inactive(modeladmin, request, queryset):
    queryset.update(stage="INACTIVE")


@admin.display(description="Sync Timeslots With Certificate")
def sync_timeslots(modeladmin, request, queryset):
    cohorts = queryset.all()
    count = 0
    for c in cohorts:
        x = ImportCohortTimeSlots(c.id)
        x.clean()
        ids = x.sync()

        logger.info(f"{len(ids)} timeslots created for cohort {str(c.slug)}")
        if len(ids) > 0:
            count += 1

    messages.add_message(request, messages.INFO, f"{count} of {cohorts.count()} cohorts timeslots were updated")


class CohortForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(CohortForm, self).__init__(*args, **kwargs)
        self.fields["timezone"] = forms.ChoiceField(choices=timezones)


@admin.display(description="Add cohort slug to active campaign")
def add_cohort_slug_to_active_campaign(modeladmin, request, queryset):
    cohorts = queryset.all()
    for cohort in cohorts:
        add_cohort_slug_as_acp_tag.delay(cohort.id, cohort.academy.id)


def get_attendancy_logs(modeladmin, request, queryset):
    for x in queryset:
        get_attendancy_log.delay(x.id)


cohort_actions = [
    sync_tasks,
    mark_as_ended,
    mark_as_started,
    mark_as_inactive,
    sync_timeslots,
    add_cohort_slug_to_active_campaign,
    get_attendancy_logs,
]

if os.getenv("ENVIRONMENT") == "DEVELOPMENT":
    pass


@admin.display(description="Link randomly relations to cohorts")
def link_randomly_relations_to_cohorts(modeladmin, request, queryset):
    academies_instances = {}
    schedules_instances = {}
    cohorts = queryset.all()

    if not cohorts:
        return

    for cohort in cohorts:

        if not cohort.syllabus_version:
            if (
                cohort.academy.id in academies_instances
                and "syllabus_versions" in academies_instances[cohort.academy.id]
            ):
                syllabus_versions = academies_instances[cohort.academy.id]["syllabus_versions"]
            else:
                syllabus_versions = SyllabusVersion.objects.filter(
                    Q(syllabus__academy_owner=cohort.academy) | Q(syllabus__private=False)
                )

            if not syllabus_versions:
                continue

            syllabus_version = choice(list(syllabus_versions))

            x = Cohort.objects.filter(id=cohort.id).first()
            x.syllabus_version = syllabus_version
            x.save()

        else:
            syllabus_version = cohort.syllabus_version

        if not cohort.schedule:
            if syllabus_version.syllabus.id in schedules_instances:
                schedules = schedules_instances[syllabus_version.syllabus.id]
            else:
                schedules = SyllabusSchedule.objects.filter(syllabus=syllabus_version.syllabus)

            if not schedules:
                continue

            schedule = choice(list(schedules))

            x = Cohort.objects.filter(id=cohort.id).first()
            x.schedule = schedule
            x.save()


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    form = CohortForm
    search_fields = ["slug", "name", "academy__city__name"]
    list_display = ("id", "slug", "stage", "name", "kickoff_date", "syllabus_version", "schedule", "academy")
    list_filter = ["stage", "academy__slug", "schedule__name", "syllabus_version__version"]

    if os.getenv("ENV") == "development":
        actions = cohort_actions + [link_randomly_relations_to_cohorts]
    else:
        actions = cohort_actions

    def academy_name(self, obj):
        return obj.academy.name

    def certificate_name(self, obj):
        return obj.certificate.slug + ".v" + str(obj.version)


@admin.display(description="Sync from Github")
def pull_from_github(modeladmin, request, queryset):
    all_syllabus = queryset.all()

    credentials = None
    try:
        credentials = request.user.credentialsgithub
    except Exception:
        logger.error("No github credentials found")
        messages.error(request, "No github credentials found")

    else:
        for syl in all_syllabus:
            # /repos/:owner/:repo/contents/:path
            regex = r"github\.com\/([0-9a-zA-Z-]+)\/([0-9a-zA-Z-]+)\/blob\/([0-9a-zA-Z-]+)\/([0-9a-zA-Z-\/\.]+)"
            matches = re.findall(regex, syl.github_url)

            if matches is None:
                logger.error(
                    "Invalid github url, make sure it follows this format: "
                    "https://github.com/:user/:repo/blob/:branch/:path"
                )
                messages.error(
                    request,
                    "Invalid github url, make sure it follows this format: "
                    "https://github.com/:user/:repo/blob/:branch/:path",
                )
                continue

            headers = {"Authorization": f"token {credentials.token}"}
            response = requests.get(
                f"https://api.github.com/repos/{matches[0][0]}/{matches[0][1]}/contents/{matches[0][3]}?ref="
                + matches[0][2],
                headers=headers,
                timeout=2,
            )
            if response.status_code == 200:
                _file = response.json()
                syl.json = json.loads(base64.b64decode(_file["content"]).decode())
                syl.save()
            else:
                logger.error(
                    f"Error {response.status_code} updating syllabus from github, make sure you have the "
                    "correct access rights to the repository"
                )
                messages.error(
                    request,
                    f"Error {response.status_code} updating syllabus from github, make sure you have the "
                    "correct access rights to the repository",
                )


@admin.register(Syllabus)
class SyllabusAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "name",
        "academy_owner",
        "private",
        "github_url",
        "duration_in_hours",
        "duration_in_days",
        "week_hours",
        "logo",
    )
    actions = [pull_from_github]


def test_syllabus_integrity(modeladmin, request, queryset):
    syllabus_versions = queryset.all()
    for version in syllabus_versions:
        version.integrity_status = "PENDING"
        version.integrity_check_at = timezone.now()
        version.save()
        try:
            report = test_syllabus(version.json)
            version.integrity_report = report.serialize()
            if report.http_status() == 200:
                version.integrity_status = "OK"
            else:
                version.integrity_status = "ERROR"
            version.save()

        except Exception as e:
            version.integrity_report = {"errors": [str(e)], "warnings": []}
            version.integrity_status = "ERROR"
            version.save()
            raise e


def async_test_syllabus_integrity(modeladmin, request, queryset):
    syllabus_versions = queryset.all()
    for version in syllabus_versions:
        async_test_syllabus.delay(version.syllabus.slug, version.version)


@admin.register(SyllabusVersion)
class SyllabusVersionAdmin(admin.ModelAdmin):
    list_display = ("version", "syllabus", "integrity", "owner")
    search_fields = ["syllabus__name", "syllabus__slug"]
    list_filter = ["syllabus__private", "syllabus__academy_owner"]
    actions = [
        test_syllabus_integrity,
        async_test_syllabus_integrity,
    ]

    def owner(self, obj):
        if obj.syllabus.academy_owner is None:
            return format_html('<span class="badge bg-error">No academy owner</span>')

        return format_html(f"<span>{obj.syllabus.academy_owner.name}</span>")

    def integrity(self, obj):
        colors = {
            "PENDING": "bg-warning",
            "OK": "bg-success",
            "ERROR": "bg-error",
            "WARNING": "bg-warning",
        }
        when = "Never tested"
        if obj.integrity_check_at is not None:
            when = from_now(obj.integrity_check_at) + " ago"
        return format_html(
            f"""<table>
            <p class='d-block badge {colors[obj.integrity_status]}'>{obj.integrity_status}</p>
            <small>{when}</small>
</table>"""
        )


class CohortTimeSlotForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(CohortTimeSlotForm, self).__init__(*args, **kwargs)
        self.fields["timezone"] = forms.ChoiceField(choices=timezones)


@admin.register(CohortTimeSlot)
class CohortTimeSlotAdmin(admin.ModelAdmin):
    form = CohortTimeSlotForm
    list_display = ("cohort", "timezone", "starting_at", "ending_at", "recurrent", "recurrency_type")
    list_filter = ["cohort__academy__slug", "timezone", "recurrent", "recurrency_type"]
    search_fields = ["cohort__slug", "timezone", "cohort__name", "cohort__academy__city__name"]


@admin.display(description="Replicate same timeslots in all academies")
def replicate_in_all(modeladmin, request, queryset: QuerySet[SyllabusSchedule]):
    from django.contrib import messages

    without_timezone_slugs = []
    already_exist_schedule_name = []
    syllabus_schedules = queryset.all()
    academies = Academy.objects.all()

    for syllabus_schedule in syllabus_schedules:
        academy_id = syllabus_schedule.academy.id

        for academy in academies:
            if academy.id == academy_id:
                continue

            if not academy.timezone:
                without_timezone_slugs.append(academy.slug)
                continue

            schedule_kwargs = {
                "academy": academy,
                "name": syllabus_schedule.name,
                "schedule_type": syllabus_schedule.schedule_type,
                "description": syllabus_schedule.description,
                "syllabus": syllabus_schedule.syllabus,
            }

            if SyllabusSchedule.objects.filter(**schedule_kwargs).first():
                already_exist_schedule_name.append(f"{academy.slug}/{syllabus_schedule.name}")
                continue

            replica_of_schedule = SyllabusSchedule(**schedule_kwargs)
            replica_of_schedule.save(force_insert=True)

            timeslots = SyllabusScheduleTimeSlot.objects.filter(schedule=syllabus_schedule)

            for timeslot in timeslots:
                replica_of_timeslot = SyllabusScheduleTimeSlot(
                    recurrent=timeslot.recurrent,
                    starting_at=timeslot.starting_at,
                    ending_at=timeslot.ending_at,
                    schedule=replica_of_schedule,
                    timezone=academy.timezone,
                )

                replica_of_timeslot.save(force_insert=True)

    if without_timezone_slugs and already_exist_schedule_name:
        messages.add_message(
            request,
            messages.ERROR,
            f'The following academies ({", ".join(without_timezone_slugs)}) was skipped because it doesn\'t '
            "have a timezone assigned and the following syllabus schedules "
            f'({", ".join(already_exist_schedule_name)}) was skipped because it already exists',
        )

    elif without_timezone_slugs:
        messages.add_message(
            request,
            messages.ERROR,
            f'The following academies ({", ".join(without_timezone_slugs)}) was skipped because it doesn\'t '
            "have a timezone assigned",
        )

    elif already_exist_schedule_name:
        messages.add_message(
            request,
            messages.ERROR,
            f'The following syllabus schedules ({", ".join(already_exist_schedule_name)}) was skipped '
            "because it already exists",
        )

    else:
        messages.add_message(request, messages.INFO, "All academies in sync with those syllabus schedules")


@admin.register(SyllabusSchedule)
class SyllabusScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "academy")
    list_filter = ["name", "academy__slug", "schedule_type"]
    search_fields = ["name", "academy__slug", "schedule_type"]
    actions = [replicate_in_all]


class SyllabusScheduleTimeSlotForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(SyllabusScheduleTimeSlotForm, self).__init__(*args, **kwargs)
        self.fields["timezone"] = forms.ChoiceField(choices=timezones)


@admin.register(SyllabusScheduleTimeSlot)
class SyllabusScheduleTimeSlotAdmin(admin.ModelAdmin):
    form = SyllabusScheduleTimeSlotForm
    list_display = ("id", "schedule", "timezone", "starting_at", "ending_at", "recurrent", "recurrency_type")
    list_filter = ["schedule__name", "timezone", "recurrent", "recurrency_type"]
    search_fields = ["schedule__name", "timezone", "schedule__name"]

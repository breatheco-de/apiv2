import pytz, logging
from django.contrib import admin
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from .models import Academy, Certificate, Cohort, CohortUser, Country, City, UserAdmissions, Syllabus, AcademyCertificate, CohortTimeSlot, CertificateTimeSlot
from .actions import sync_cohort_timeslots
from breathecode.assignments.actions import sync_student_tasks

logger = logging.getLogger(__name__)

# Register your models here.
admin.site.site_header = "BreatheCode"
admin.site.index_title = "Administration Portal"
admin.site.site_title = "Administration Portal"

timezones = [(x, x) for x in pytz.common_timezones]


@admin.register(UserAdmissions)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')


class AcademyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AcademyForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            self.fields['timezone'] = forms.ChoiceField(choices=timezones)


@admin.register(Academy)
class AcademyAdmin(admin.ModelAdmin):
    form = AcademyForm
    list_display = ('slug', 'name', 'city')


@admin.register(AcademyCertificate)
class AcademyCertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate', 'academy')
    list_filter = ['certificate__slug', 'academy__slug']


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'duration_in_hours')


def make_assistant(modeladmin, request, queryset):
    cohort_users = queryset.all()
    for cu in cohort_users:
        cu.role = "ASSISTANT"
        cu.save()


make_assistant.short_description = "Make it an ASSISTANT"


def make_teacher(modeladmin, request, queryset):
    cohort_users = queryset.all()
    for cu in cohort_users:
        cu.role = "TEACHER"
        cu.save()


make_teacher.short_description = "Make it a TEACHER"


def make_student(modeladmin, request, queryset):
    cohort_users = queryset.all()
    for cu in cohort_users:
        cu.role = "STUDENT"
        cu.save()


make_student.short_description = "Make it a STUDENT"


def make_edu_stat_active(modeladmin, request, queryset):
    cohort_users = queryset.all()
    for cu in cohort_users:
        cu.educational_status = "ACTIVE"
        cu.save()


make_edu_stat_active.short_description = "Educational_status = ACTIVE"


def make_edu_stat_graduate(modeladmin, request, queryset):
    cohort_users = queryset.all()
    for cu in cohort_users:
        cu.educational_status = "GRADUATED"
        cu.save()


make_edu_stat_graduate.short_description = "Educational_status = GRADUATED"


@admin.register(CohortUser)
class CohortUserAdmin(admin.ModelAdmin):
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name', 'cohort__name',
        'cohort__slug'
    ]
    list_display = ('get_student', 'cohort', 'role', 'educational_status',
                    'finantial_status', 'created_at')
    list_filter = ['role', 'educational_status', 'finantial_status']
    raw_id_fields = ["user", "cohort"]
    actions = [
        make_assistant, make_teacher, make_student, make_edu_stat_active
    ]

    def get_student(self, obj):
        return obj.user.first_name + " " + obj.user.last_name + "(" + obj.user.email + ")"


def sync_tasks(modeladmin, request, queryset):
    cohort_ids = queryset.values_list('id', flat=True)
    cohort_user = CohortUser.objects.filter(cohort__id__in=[cohort_ids])
    for cu in cohort_user:
        sync_student_tasks(cu.user)


sync_tasks.short_description = "Sync Tasks"


def mark_as_ended(modeladmin, request, queryset):
    issues = queryset.update(stage='ENDED')


mark_as_ended.short_description = "Mark as ENDED"


def mark_as_started(modeladmin, request, queryset):
    issues = queryset.update(stage='STARTED')


mark_as_started.short_description = "Mark as STARTED"


def mark_as_innactive(modeladmin, request, queryset):
    issues = queryset.update(stage='INACTIVE')


mark_as_innactive.short_description = "Mark as INACTIVE"


def sync_timeslots(modeladmin, request, queryset):
    cohorts = queryset.all()
    count = 0
    for c in cohorts:
        ids = sync_cohort_timeslots(c.id)
        logger.info(f"{len(ids)} timeslots created for cohort {str(c.slug)}")
        if len(ids) > 0:
            count += 1

    messages.add_message(
        request, messages.INFO,
        f'{count} of {cohorts.count()} cohorts timeslots were updated')


sync_timeslots.short_description = "Sync Timeslots With Certificate ⏱ "


class CohortForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(CohortForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            self.fields['timezone'] = forms.ChoiceField(choices=timezones)


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    form = CohortForm
    search_fields = ['slug', 'name', 'academy__city__name']
    list_display = ('id', 'slug', 'stage', 'name', 'kickoff_date', 'syllabus')
    list_filter = ['stage', 'academy__slug', 'syllabus__certificate__slug']
    actions = [
        sync_tasks, mark_as_ended, mark_as_started, mark_as_innactive,
        sync_timeslots
    ]

    def academy_name(self, obj):
        return obj.academy.name

    def certificate_name(self, obj):
        return obj.certificate.slug + ".v" + str(obj.version)


def sync_with_github(modeladmin, request, queryset):
    all_syllabus = queryset.all()

    credentials = None
    try:
        credentials = request.user.credentialsgithub
    except Exception:
        logger.error("No github credentials found")
        messages.error(request, 'No github credentials found')

    else:
        for syl in all_syllabus:
            #/repos/:owner/:repo/contents/:path
            regex = r"github\.com\/([0-9a-zA-Z-]+)\/([0-9a-zA-Z-]+)\/blob\/([0-9a-zA-Z-]+)\/([0-9a-zA-Z-\/\.]+)"
            matches = re.findall(regex, syl.github_url)
            print(matches, syl.github_url)
            if matches is None:
                logger.error(
                    f'Invalid github url, make sure it follows this format: https://github.com/:user/:repo/blob/:branch/:path'
                )
                messages.error(
                    request,
                    'Invalid github url, make sure it follows this format: https://github.com/:user/:repo/blob/:branch/:path'
                )
                continue

            headers = {"Authorization": f"token {credentials.token}"}
            response = requests.get(
                f"https://api.github.com/repos/{matches[0][0]}/{matches[0][1]}/contents/{matches[0][3]}?ref="
                + matches[0][2],
                headers=headers)
            if response.status_code == 200:
                _file = response.json()
                syl.json = json.loads(
                    base64.b64decode(_file["content"]).decode())
                syl.save()
            else:
                logger.error(
                    f'Error {response.status_code} updating syllabus from github, make sure you have the correct access rights to the repository'
                )
                messages.error(
                    request,
                    f'Error {response.status_code} updating syllabus from github, make sure you have the correct access rights to the repository'
                )


sync_with_github.short_description = "Sync from Github"


@admin.register(Syllabus)
class SyllabusAdmin(admin.ModelAdmin):
    list_display = ('slug', 'certificate', 'academy_owner', 'version')
    actions = [sync_with_github]


@admin.register(CohortTimeSlot)
class CohortTimeSlotAdmin(admin.ModelAdmin):
    list_display = ('cohort', 'starting_at', 'ending_at', 'recurrent',
                    'recurrency_type')
    list_filter = ['cohort__academy__slug', 'recurrent', 'recurrency_type']
    search_fields = [
        'cohort__slug', 'cohort__name', 'cohort__academy__city__name'
    ]


def replicate_in_all(modeladmin, request, queryset):
    cert_timeslot = queryset.all()
    academies = Academy.objects.all()
    for a in academies:
        to_filter = {}
        for c in cert_timeslot:
            # delete all timeslots for that academy and certificate ONLY the first time
            if c.certificate.slug not in to_filter:
                CertificateTimeSlot.objects.filter(certificate=c.certificate,
                                                   academy=a).delete()
                to_filter[c.certificate.slug] = True
            # and then re add the timeslots one by one
            new_timeslot = CertificateTimeSlot(recurrent=c.recurrent,
                                               starting_at=c.starting_at,
                                               ending_at=c.ending_at,
                                               certificate=c.certificate,
                                               academy=a)
            new_timeslot.save()

        logger.info(f"All academies in sync with those timeslots")

    messages.add_message(request, messages.INFO,
                         f'All academies in sync with those timeslots')


replicate_in_all.short_description = "Replicate same timeslots in all academies"


@admin.register(CertificateTimeSlot)
class CertificateTimeSlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'certificate', 'starting_at', 'ending_at', 'academy',
                    'recurrent', 'recurrency_type')
    list_filter = [
        'certificate__slug', 'academy__slug', 'recurrent', 'recurrency_type'
    ]
    search_fields = [
        'certificate__slug', 'certificate__name', 'academy__slug',
        'academy__name'
    ]
    actions = [replicate_in_all]

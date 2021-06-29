import logging, requests, base64, re, json, csv
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from breathecode.admissions.admin import CohortAdmin
from .models import Badge, Specialty, UserSpecialty, UserProxy, LayoutDesign, CohortProxy
from .tasks import remove_screenshot, reset_screenshot, generate_cohort_certificates
from .actions import generate_certificate
from django.http import HttpResponse

logger = logging.getLogger(__name__)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')


@admin.register(LayoutDesign)
class LayoutDesignAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')


def screenshot(modeladmin, request, queryset):
    from django.contrib import messages

    certificate_ids = queryset.values_list('id', flat=True)
    for cert_id in certificate_ids:
        reset_screenshot.delay(cert_id)
    messages.success(request, message="Screenshots scheduled correctly")


screenshot.short_description = "🔄 RETAKE Screenshot"


def delete_screenshot(modeladmin, request, queryset):
    from django.contrib import messages

    certificate_ids = queryset.values_list('id', flat=True)
    for cert_id in certificate_ids:
        remove_screenshot.delay(cert_id)
    messages.success(request, message="Screenshots scheduled for deletion")


delete_screenshot.short_description = "⛔️ DELETE Screenshot"


def export_user_specialty_csv(self, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=certificates.csv'
    writer = csv.writer(response)
    writer.writerow([
        'First Name', 'Last Name', 'Specialty', 'Academy', 'Cohort',
        'Certificate', 'PDF'
    ])
    for obj in queryset:
        row = writer.writerow([
            obj.user.first_name, obj.user.last_name, obj.specialty.name,
            obj.academy.name, obj.cohort.name,
            f"https://certificate.breatheco.de/{obj.token}",
            f"https://certificate.breatheco.de/pdf/{obj.token}"
        ])

    return response


export_user_specialty_csv.short_description = "⬇️ Export Selected"


@admin.register(UserSpecialty)
class UserSpecialtyAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty', 'expires_at', 'academy', 'cohort',
                    'pdf', 'preview')
    list_filter = ['specialty', 'academy__slug', 'cohort__slug']
    raw_id_fields = ["user"]
    actions = [screenshot, delete_screenshot, export_user_specialty_csv]

    def pdf(self, obj):
        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='https://certificate.breatheco.de/pdf/{obj.token}'>pdf</a>"
        )

    def preview(self, obj):
        if obj.preview_url is None or obj.preview_url == "":
            return format_html("No available")

        return format_html(
            "<a rel='noopener noreferrer' target='_blank' href='{url}'>preview</a>",
            url=obj.preview_url)

    def get_readonly_fields(self, request, obj=None):
        return ['token', 'expires_at']


def user_bulk_certificate(modeladmin, request, queryset):
    from django.contrib import messages

    users = queryset.all()
    try:
        for u in users:
            logger.debug(f"Generating certificate for user {u.id}")
            generate_certificate(u)
        messages.success(request, message="Certificates generated sucessfully")
    except Exception as e:
        logger.exception("Problem generating certificates")
        messages.error(request, message=str(e))


user_bulk_certificate.short_description = "🎖 Generate Student Certificate"


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    actions = [user_bulk_certificate]


def cohort_bulk_certificate(modeladmin, request, queryset):
    from django.contrib import messages

    cohort_ids = queryset.values_list('id', flat=True)
    for _id in cohort_ids:
        logger.debug(f"Scheduling certificate generation for cohort {_id}")
        generate_cohort_certificates.delay(_id)

    messages.success(request, message="Scheduled certificate generation")


cohort_bulk_certificate.short_description = "🥇 Generate Cohort Certificates"


@admin.register(CohortProxy)
class CohortAdmin(CohortAdmin):
    list_display = ('slug', 'name', 'stage')
    actions = [cohort_bulk_certificate]

import logging, csv
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from breathecode.admissions.admin import CohortAdmin as AdmissionsCohortAdmin
from .models import Badge, Specialty, UserSpecialty, UserProxy, LayoutDesign, CohortProxy
from .tasks import remove_screenshot, reset_screenshot, generate_cohort_certificates
from .actions import generate_certificate, generate_certificate_ignoring_tasks
from django.http import HttpResponse
import re

logger = logging.getLogger(__name__)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("slug", "name")


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ("slug", "name")


@admin.register(LayoutDesign)
class LayoutDesignAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "academy", "template", "default")
    list_filter = ["academy__slug"]

    def template(self, obj):
        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='{obj.background_url}'>view template</a>"
        )

    def default(self, obj):
        if obj.is_default:
            return "✅ default"
        else:
            return "not default"


@admin.display(description="🔄 RETAKE Screenshot")
def screenshot(modeladmin, request, queryset):
    from django.contrib import messages

    certificate_ids = queryset.values_list("id", flat=True)
    for cert_id in certificate_ids:
        reset_screenshot.delay(cert_id)
    messages.success(request, message="Screenshots scheduled correctly")


@admin.display(description="⛔️ DELETE Screenshot")
def delete_screenshot(modeladmin, request, queryset):
    from django.contrib import messages

    certificate_ids = queryset.values_list("id", flat=True)
    for cert_id in certificate_ids:
        remove_screenshot.delay(cert_id)
    messages.success(request, message="Screenshots scheduled for deletion")


@admin.display(description="⬇️ Export Selected")
def export_user_specialty_csv(self, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=certificates.csv"
    writer = csv.writer(response)
    writer.writerow(["First Name", "Last Name", "Specialty", "Academy", "Cohort", "Certificate", "PDF"])
    for obj in queryset:
        writer.writerow(
            [
                obj.user.first_name,
                obj.user.last_name,
                obj.specialty.name,
                obj.academy.name,
                obj.cohort.name,
                f"https://certificate.4geeks.com/{obj.token}",
                f"https://certificate.4geeks.com/pdf/{obj.token}",
            ]
        )

    return response


@admin.display(description="🎓 Generate Certificates (Ignore Pending Tasks)")
def generate_certificates_ignoring_tasks(modeladmin, request, queryset):
    from django.contrib import messages
    from capyc.rest_framework.exceptions import ValidationException

    success_count = 0
    error_count = 0
    errors = []

    for user_specialty in queryset:
        try:
            if not user_specialty.user:
                errors.append(f"UserSpecialty {user_specialty.id}: No user associated")
                error_count += 1
                continue

            if not user_specialty.cohort:
                errors.append(f"UserSpecialty {user_specialty.id}: No cohort associated")
                error_count += 1
                continue

            logger.debug(
                f"Generating certificate ignoring tasks for user {user_specialty.user.id} "
                f"in cohort {user_specialty.cohort.id}"
            )
            generate_certificate_ignoring_tasks(user_specialty.user, user_specialty.cohort, user_specialty.layout)
            success_count += 1

        except ValidationException as e:
            error_msg = f"UserSpecialty {user_specialty.id} (user: {user_specialty.user.email}): {str(e)}"
            errors.append(error_msg)
            error_count += 1
            logger.exception(error_msg)
        except Exception as e:
            error_msg = f"UserSpecialty {user_specialty.id} (user: {user_specialty.user.email}): {str(e)}"
            errors.append(error_msg)
            error_count += 1
            logger.exception(error_msg)

    # Show results
    if success_count > 0:
        messages.success(
            request, message=f"Successfully generated {success_count} certificate(s) ignoring pending tasks"
        )

    if error_count > 0:
        error_message = f"Failed to generate {error_count} certificate(s). Errors: " + " | ".join(errors[:5])
        if len(errors) > 5:
            error_message += f" ... and {len(errors) - 5} more errors"
        messages.error(request, message=error_message)


@admin.register(UserSpecialty)
class UserSpecialtyAdmin(admin.ModelAdmin):
    search_fields = ["user__email", "user__first_name", "user__last_name", "cohort__name", "cohort__slug"]
    list_display = ("user", "specialty", "current_status", "expires_at", "academy", "cohort", "pdf", "preview")
    list_filter = ["specialty", "academy__slug", "cohort__slug"]
    raw_id_fields = ["user"]
    actions = [screenshot, delete_screenshot, export_user_specialty_csv, generate_certificates_ignoring_tasks]

    def current_status(self, obj):
        colors = {
            "PENDING": "bg-warning",
            "PERSISTED": "bg-success",
            "ERROR": "bg-error",
            None: "bg-warning",
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
        <tr><td colspan='1'>{status}</td></tr>
        </table>"""
        )

    current_status.short_description = "Status"

    def pdf(self, obj):
        if obj.status == "PERSISTED":
            return format_html(
                f"<a rel='noopener noreferrer' target='_blank' href='https://certificate.4geeks.com/pdf/{obj.token}'>pdf</a>"
            )
        else:
            return format_html('<span style="color: #dc3545;">check errors</span>')

    def preview(self, obj):
        if obj.preview_url is None or obj.preview_url == "":
            return format_html("No available")

        return format_html("<a rel='noopener noreferrer' target='_blank' href='{url}'>preview</a>", url=obj.preview_url)

    def get_readonly_fields(self, request, obj=None):
        return ["token", "expires_at"]


@admin.display(description="🎖 Generate Student Certificate")
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


@admin.register(UserProxy)
class UserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name")
    actions = [user_bulk_certificate]


@admin.display(description="🥇 Generate Cohort Certificates")
def cohort_bulk_certificate(modeladmin, request, queryset):
    from django.contrib import messages

    cohort_ids = queryset.values_list("id", flat=True)
    for _id in cohort_ids:
        logger.debug(f"Scheduling certificate generation for cohort {_id}")
        generate_cohort_certificates.delay(_id)

    messages.success(request, message="Scheduled certificate generation")


@admin.register(CohortProxy)
class CohortAdmin(AdmissionsCohortAdmin):
    list_display = ("id", "slug", "stage", "name", "kickoff_date", "syllabus_version", "schedule")
    actions = [cohort_bulk_certificate]

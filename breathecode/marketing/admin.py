import logging
import secrets

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from django.utils.html import format_html

from breathecode.services.activecampaign import ActiveCampaign
from breathecode.utils import AdminExportCsvMixin
from breathecode.utils.admin import change_field
from capyc.rest_framework.exceptions import ValidationException

from .actions import (
    bind_formentry_with_webhook,
    delete_tag,
    get_facebook_lead_info,
    register_new_lead,
    save_get_geolocal,
    sync_automations,
    sync_tags,
    test_ac_connection,
)
from .models import (
    AcademyAlias,
    AcademyProxy,
    ActiveCampaignAcademy,
    ActiveCampaignWebhook,
    Automation,
    Course,
    CourseTranslation,
    Downloadable,
    FormEntry,
    LeadGenerationApp,
    ShortLink,
    Tag,
    UTMField,
)
from .tasks import async_activecampaign_webhook, async_update_deal_custom_fields

# Register your models here.

logger = logging.getLogger(__name__)


@admin.display(description="♼ Test connection to Active Campaign")
def test_ac(modeladmin, request, queryset):
    entries = queryset.all()
    try:
        for entry in entries:
            test_ac_connection(entry)
        messages.success(request, message="Connection was a success")
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


@admin.display(description="♼ Sync AC Tags")
def sync_ac_tags(modeladmin, request, queryset):
    entries = queryset.all()
    try:
        for entry in entries:
            sync_tags(entry)
        messages.success(request, message="Tags imported successfully")
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


@admin.display(description="♼ Sync AC Automations")
def sync_ac_automations(modeladmin, request, queryset):
    entries = queryset.all()
    _result = {"success": [], "error": []}
    try:
        for entry in entries:
            if sync_automations(entry):
                _result["success"].append(entry.academy.name)
            else:
                _result["error"].append(entry.academy.name)

        _errors = ", ".join(_result["error"])
        _success = ", ".join(_result["success"])
        messages.success(request, message=f"Errored in {_errors}. Succeded in: {_success}")
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


class CustomForm(forms.ModelForm):

    class Meta:
        model = ActiveCampaignAcademy
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(CustomForm, self).__init__(*args, **kwargs)
        self.fields["event_attendancy_automation"].queryset = Automation.objects.filter(
            ac_academy=self.instance.id
        )  # or something else


@admin.register(ActiveCampaignAcademy)
class ACAcademyAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    form = CustomForm
    search_fields = ["academy__name", "academy__slug"]
    list_display = ("id", "academy", "ac_url", "sync_status", "last_interaction_at", "sync_message")
    list_filter = ["academy__slug", "sync_status"]
    actions = [test_ac, sync_ac_tags, sync_ac_automations]


@admin.register(AcademyAlias)
class AcademyAliasAdmin(admin.ModelAdmin):
    search_fields = ["slug", "active_campaign_slug", "academy__slug", "academy__title"]
    list_display = ("slug", "active_campaign_slug", "academy")
    list_filter = ["academy__slug"]


def generate_original_alias(modeladmin, request, queryset):
    academies = queryset.all()
    for a in academies:
        slug = a.active_campaign_slug
        if slug is None:
            slug = a.slug

        if AcademyAlias.objects.filter(slug=a.slug).first() is None:
            AcademyAlias.objects.create(slug=a.slug, active_campaign_slug=slug, academy=a)
            messages.add_message(request, messages.INFO, f"Alias {a.slug} successfully created")
        else:
            messages.add_message(request, messages.ERROR, f"Alias {a.slug} already exists")


@admin.register(AcademyProxy)
class AcademyAdmin(admin.ModelAdmin):
    list_display = ("slug", "name")
    actions = [generate_original_alias]


def send_to_active_campaign(modeladmin, request, queryset):
    entries = queryset.all()
    total = {"error": 0, "persisted": 0}
    entry = None
    try:
        for entry in entries:
            entry = register_new_lead(entry.to_form_data())
            if entry.storage_status == "PERSISTED":
                total["persisted"] += 1
            else:
                total["error"] += 1

    except Exception as e:
        total["error"] += 1
        entry.storage_status = "ERROR"
        entry.storage_status_text = str(e)
        entry.save()

    messages.add_message(
        request,
        messages.SUCCESS,
        f"Persisted leads: {total['persisted']}. Not persisted: {total['error']}. You can check each lead storage_status_text for details.",
    )


@admin.display(description="♺ Download more info from facebook")
def fetch_more_facebook_info(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entries:
        get_facebook_lead_info(entry.id)


@admin.display(description="🌐 Get GEO info")
def sync_contact_custom_fields_with_deal(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entries:
        if not entry.ac_contact_id or not entry.ac_deal_id:
            messages.error(request, message=f"FormEntry {str(entry.id)} is missing deal_id or contact_id")
            return None

    for entry in entries:
        # update_deal_custom_fields(entry.ac_deal_id, entry.ac_contact_id)
        async_update_deal_custom_fields.delay(entry.id)


def get_geoinfo(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entries:

        form_enty = {
            "latitude": entry.latitude,
            "longitude": entry.longitude,
        }
        save_get_geolocal(entry, form_enty)


class PPCFilter(SimpleListFilter):
    title = "Source"  # or use _('country') for translated title
    parameter_name = "source"

    def lookups(self, request, model_admin):
        mediums = ["From PPC", "Course Report"]
        return [(m, m) for m in mediums]

    def queryset(self, request, queryset):
        if self.value() == "From PPC":
            return queryset.filter(gclid__isnull=False)
        if self.value() == "Course Report":
            return queryset.filter(utm_medium="coursereportschoolpage")


@admin.register(FormEntry)
class FormEntryAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = ["email", "first_name", "last_name", "phone", "utm_campaign", "utm_url", "attribution_id"]
    list_display = (
        "id",
        "_attribution_id",
        "_storage_status",
        "created_at",
        "first_name",
        "last_name",
        "email",
        "location",
        "course",
        "academy",
        "country",
        "city",
        "utm_medium",
        "utm_url",
        "gclid",
        "tags",
    )
    list_filter = [
        "storage_status",
        "location",
        "course",
        "deal_status",
        PPCFilter,
        "lead_generation_app",
        "utm_medium",
        "utm_campaign",
        "utm_source",
    ]
    actions = (
        [
            send_to_active_campaign,
            get_geoinfo,
            fetch_more_facebook_info,
            sync_contact_custom_fields_with_deal,
            "async_export_as_csv",
        ]
        + change_field(
            [
                "bogota-colombia",
                "mexicocity-mexico",
                "quito-ecuador",
                "buenosaires-argentina",
                "caracas-venezuela",
                "online",
            ],
            name="location",
        )
        + change_field(["full-stack", "datascience-ml", "cybersecurity"], name="course")
        + change_field(["REJECTED", "DUPLICATED", "ERROR"], name="storage_status")
    )

    def _attribution_id(self, obj):

        _html = f"<small>{obj.attribution_id}</small>"
        if obj.won_at is not None:
            colors = {
                "WON": "bg-success",
                "LOST": "bg-error",
                None: "",
            }
            _html += f"<p class='{colors[obj.deal_status]}'>WON</p>"

        return format_html(_html)

    def _storage_status(self, obj):
        colors = {
            "PUBLISHED": "bg-success",
            "OK": "bg-success",
            "ERROR": "bg-error",
            "WARNING": "bg-warning",
            "DUPLICATED": "",
            None: "bg-warning",
            "DRAFT": "bg-error",
            "PENDING_TRANSLATION": "bg-error",
            "PENDING": "bg-warning",
            "WARNING": "bg-warning",
            "NOT_STARTED": "bg-error",
            "UNLISTED": "bg-warning",
        }

        def from_status(s):
            if s in colors:
                return colors[s]
            return ""

        return format_html(
            f"<p class='{from_status(obj.storage_status)}'>{obj.storage_status}</p><small>{obj.storage_status_text}</small>"
        )


def add_dispute(modeladmin, request, queryset):
    queryset.update(disputed_at=timezone.now())


def remove_dispute(modeladmin, request, queryset):
    queryset.update(disputed_at=None)


def delete_from_everywhere(modeladmin, request, queryset):

    for t in queryset:
        slug = t.slug
        try:
            if delete_tag(t) == True:
                messages.add_message(request, messages.INFO, f"Tag {slug} successully deleted")
            else:
                messages.add_message(request, messages.ERROR, f"Error deleding tag {slug}")
        except Exception as e:
            messages.add_message(request, messages.ERROR, f"Error deleding tag {slug}: {str(e)}")


def upload_to_active_campaign(modeladmin, request, queryset):

    for t in queryset:
        slug = t.slug
        try:
            ac_academy = t.ac_academy
            if ac_academy is None:
                raise ValidationException(
                    f"Invalid ac_academy for this tag {t.slug}", code=400, slug="invalid-ac_academy"
                )

            client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
            data = client.create_tag(t.slug, description=t.description)
            t.acp_id = data["id"]
            t.subscribers = 0
            t.save()
            messages.add_message(request, messages.INFO, f"Tag {t.slug} successully uploaded")
        except Exception as e:
            messages.add_message(request, messages.ERROR, f"Error uploading tag {slug}: {str(e)}")


@admin.display(description='Prepend "tech-" on slug')
def prepend_tech_on_name(modeladmin, request, queryset):

    for t in queryset:
        if t.slug[:5] == "tech-":
            continue
        t.slug = "tech-" + t.slug
        t.save()


class CustomTagModelForm(forms.ModelForm):

    class Meta:
        model = Tag
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(CustomTagModelForm, self).__init__(*args, **kwargs)
        if self.instance.ac_academy is not None:
            self.fields["automation"].queryset = Automation.objects.filter(
                ac_academy=self.instance.ac_academy.id
            )  # or something else


class TagTypeFilter(SimpleListFilter):
    title = "tag_type"
    parameter_name = "tag_type"

    def lookups(self, request, model_admin):
        tags = set([c.tag_type for c in Tag.objects.filter(tag_type__isnull=False)])
        return [(c, c) for c in tags] + [("NONE", "No type")]

    def queryset(self, request, queryset):
        if self.value() == "NONE":
            return queryset.filter(tag_type__isnull=True)
        if self.value():
            return queryset.filter(tag_type__exact=self.value())


class DisputedFilter(admin.SimpleListFilter):

    title = "Disputed tag"

    parameter_name = "is_disputed"

    def lookups(self, request, model_admin):

        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):

        if self.value() == "yes":
            return queryset.filter(disputed_at__isnull=False)

        if self.value() == "no":
            return queryset.filter(disputed_at__isnull=True)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    form = CustomTagModelForm
    search_fields = ["slug"]
    list_display = ("id", "slug", "tag_type", "disputed", "ac_academy", "acp_id", "subscribers")
    list_filter = [DisputedFilter, TagTypeFilter, "ac_academy__academy__slug"]
    actions = [
        delete_from_everywhere,
        "export_as_csv",
        upload_to_active_campaign,
        add_dispute,
        remove_dispute,
        prepend_tech_on_name,
    ] + change_field(["STRONG", "SOFT", "DISCOVERY", "COHORT", "DOWNLOADABLE", "EVENT", "OTHER"], name="tag_type")

    def disputed(self, obj):
        if obj.disputed_at is not None:
            return format_html(
                f"<div><span class='badge bg-error' style='font-size: 11px;'>Will delete</span><p style='margin:0; padding: 0; font-size: 9px;'>On {obj.disputed_at.strftime('%b %d, %y')}</p></div>"
            )
        else:
            return format_html("<span class='badge'></span>")


@admin.register(Automation)
class AutomationAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = ["slug", "name"]
    list_display = ("id", "acp_id", "slug", "name", "status", "entered", "exited")
    list_filter = ["status", "ac_academy__academy__slug"]
    actions = ["export_as_csv"]


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = ["slug", "destination"]
    list_display = ("id", "slug", "hits", "current_status", "active", "lastclick_at", "link")
    list_filter = ["destination_status", "active"]
    actions = ["export_as_csv"]

    def current_status(self, obj):
        colors = {
            "ACTIVE": "bg-success",
            "ERROR": "bg-error",
            "NOT_FOUND": "bg-warning",
        }

        return format_html(f"<span class='badge {colors[obj.destination_status]}'>{obj.destination_status}</span>")

    def link(self, obj):
        return format_html(
            "<a rel='noopener noreferrer' target='_blank' href='{url}'>{short_link}</a>",
            url=f"https://s.4geeks.co/s/{obj.slug}",
            short_link=f"https://s.4geeks.co/s/{obj.slug}",
        )


def bind_with_formentry(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for hook in queryset.all():
        bind_formentry_with_webhook(hook)


def async_process_hook(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for hook in queryset.all().order_by("created_at"):
        async_activecampaign_webhook.delay(hook.id)


def process_hook(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for hook in queryset.all().order_by("created_at"):
        print(f"Procesing hook: {hook.id}")
        ac_academy = hook.ac_academy
        client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
        client.execute_action(hook.id)


@admin.register(ActiveCampaignWebhook)
class ActiveCampaignWebhookAdmin(admin.ModelAdmin):
    list_display = ("id", "webhook_type", "current_status", "run_at", "created_at", "formentry")
    search_fields = ["form_entry__email", "form_entry__ac_deal_id"]
    list_filter = ["status", "webhook_type", "form_entry__location"]
    raw_id_fields = ["form_entry"]
    actions = [process_hook, async_process_hook, bind_with_formentry]

    def current_status(self, obj):
        colors = {
            "DONE": "bg-success",
            "ERROR": "bg-error",
            "PENDING": "bg-warning",
        }
        if obj.status == "DONE":
            return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")
        return format_html(
            f"<div><span class='badge {colors[obj.status]}'>{obj.status}</span></div><small>{obj.status_text}</small>"
        )

    def formentry(self, obj):
        if obj.form_entry is None:
            return "-"
        return format_html(
            f"<a href='/admin/marketing/formentry/{obj.form_entry.id}/change/'>{str(obj.form_entry)}</a>"
        )


@admin.register(Downloadable)
class DownloadableAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "academy", "status", "open_link")
    raw_id_fields = ["author"]

    def open_link(self, obj):
        return format_html(f"<a href='{obj.destination_url}' target='parent'>open link</a>")

    def status(self, obj):
        colors = {
            "ACTIVE": "bg-success",
            "NOT_FOUND": "bg-error",
        }
        return format_html(f"<span class='badge {colors[obj.destination_status]}'>{obj.destination_status}</span>")


@admin.display(description="Reset app id")
def reset_app_id(modeladmin, request, queryset):
    for app in queryset.all():
        app.app_id = secrets.token_urlsafe(16)
        app.save()


class LeadAppCustomForm(forms.ModelForm):

    class Meta:
        model = LeadGenerationApp
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(LeadAppCustomForm, self).__init__(*args, **kwargs)

        try:
            if "default_automations" in self.fields:
                self.fields["default_automations"].queryset = Automation.objects.filter(
                    ac_academy__academy__id=self.instance.academy.id
                ).exclude(
                    slug=""
                )  # or something else
            self.fields["default_tags"].queryset = Tag.objects.filter(
                ac_academy__academy__id=self.instance.academy.id
            )  # or something else
        except Exception:
            self.fields["default_automations"].queryset = Automation.objects.none()
            self.fields["default_tags"].queryset = Tag.objects.none()


@admin.register(LeadGenerationApp)
class LeadGenerationAppAdmin(admin.ModelAdmin):
    form = LeadAppCustomForm
    list_display = ("slug", "name", "academy", "status", "last_call_at", "app_id")
    readonly_fields = ("app_id",)
    actions = (reset_app_id,)

    def status(self, obj):
        colors = {
            "OK": "bg-success",
            "ERROR": "bg-error",
        }
        if obj.last_call_status is None:
            return format_html("<span class='badge'>Not yet called</span>")
        return format_html(f"<span class='badge {colors[obj.last_call_status]}'>{obj.last_call_status}</span>")


def course_module_keys_validation(course_module):
    if course_module["name"] is None or course_module["name"] == "":
        return "The module does not have a name."
    if course_module["slug"] is None or course_module["slug"] == "":
        return f'The module {course_module["name"]} does not have a slug.'
    if course_module["icon_url"] is None or course_module["icon_url"] == "":
        return f'The module {course_module["name"]} does not have an icon_url.'
    if course_module["description"] is None or course_module["description"] == "":
        return f'The module {course_module["name"]} does not have a description.'


def validate_course_modules(modeladmin, request, queryset):
    courses = queryset.all()
    try:
        for course in courses:
            modules = []
            course_translations = CourseTranslation.objects.filter(course=course.id)
            for course_translation in course_translations:
                course_modules = course_translation.course_modules
                course_modules_list = []
                for course_module in course_modules:
                    keys_validation_error = course_module_keys_validation(course_module)
                    if keys_validation_error is not None and keys_validation_error != "":
                        course.status_message = keys_validation_error
                        course.save()
                        return
                    course_modules_list.append(course_module["slug"])
                modules.append(course_modules_list)
            for module in modules:
                if modules[0] != module:
                    course.status_message = "The course translations have different modules."
                    course.save()
                    return

            course.status_message = "All course translation have the same modules"
            course.save()
    except Exception as e:
        logger.fatal(str(e))
        course.status_message = str(e)
        course.save()


@admin.register(UTMField)
class UTMFieldAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "utm_type")
    list_filter = ["utm_type", "academy__slug"]
    actions = change_field(["SOURCE", "MEDIUM", "CAMPAIGN", "CONTENT"], name="utm_type")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("slug", "academy", "status", "status_message", "visibility")
    list_filter = ["academy__slug", "status", "visibility"]
    filter_horizontal = ("syllabus",)
    raw_id_fields = ["cohort"]
    actions = [validate_course_modules]


@admin.register(CourseTranslation)
class CourseTranslationAdmin(admin.ModelAdmin):
    list_display = ("course", "lang", "title", "description")
    list_filter = ["course__academy__slug", "course__status", "course__visibility"]

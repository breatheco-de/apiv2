import logging
from django.contrib import admin, messages
from django import forms
from .models import FormEntry, Tag, Automation, ShortLink, ActiveCampaignAcademy, ActiveCampaignWebhook, AcademyAlias
from .actions import (
    register_new_lead,
    save_get_geolocal,
    get_facebook_lead_info,
    test_ac_connection,
    sync_tags,
    sync_automations,
)
from breathecode.services.activecampaign import ActiveCampaign
from django.utils.html import format_html
from django.contrib.admin import SimpleListFilter
from breathecode.utils import AdminExportCsvMixin
# Register your models here.

logger = logging.getLogger(__name__)


def test_ac(modeladmin, request, queryset):
    entries = queryset.all()
    try:
        for entry in entries:
            test_ac_connection(entry)
        messages.success(request, message="Connection was a success")
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


test_ac.short_description = "♼ Test connection to Active Campaign"


def sync_ac_tags(modeladmin, request, queryset):
    entries = queryset.all()
    try:
        for entry in entries:
            sync_tags(entry)
        messages.success(request, message="Tags imported successfully")
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


sync_ac_tags.short_description = "♼ Sync AC Tags"


def sync_ac_automations(modeladmin, request, queryset):
    entries = queryset.all()
    try:
        for entry in entries:
            sync_automations(entry)
        messages.success(request, message="Automations imported successfully")
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, message=str(e))


sync_ac_automations.short_description = "♼ Sync AC Automations"


class CustomForm(forms.ModelForm):
    class Meta:
        model = ActiveCampaignAcademy
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CustomForm, self).__init__(*args, **kwargs)
        self.fields[
            'event_attendancy_automation'].queryset = Automation.objects.filter(
                ac_academy=self.instance.id)  # or something else


@admin.register(ActiveCampaignAcademy)
class ACAcademyAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    form = CustomForm
    search_fields = ['academy__name', 'academy__slug']
    list_display = ('id', 'academy', 'ac_url', 'sync_status',
                    'last_interaction_at', 'sync_message')
    list_filter = ['academy__slug', 'sync_status']
    actions = [test_ac, sync_ac_tags, sync_ac_automations]


@admin.register(AcademyAlias)
class AcademyAliasAdmin(admin.ModelAdmin):
    search_fields = [
        'slug', 'active_campaign_slug', 'academy__slug', 'academy__title'
    ]
    list_display = ('slug', 'active_campaign_slug', 'academy')


def send_to_ac(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entries:
        register_new_lead(entry.toFormData())


send_to_ac.short_description = "⨁ Add lead to automations in AC"


def fetch_more_facebook_info(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entries:
        get_facebook_lead_info(entry.id)


fetch_more_facebook_info.short_description = "♺ Download more info from facebook"


def get_geoinfo(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entries:

        form_enty = {
            "latitude": entry.latitude,
            "longitude": entry.longitude,
        }
        save_get_geolocal(entry, form_enty)


get_geoinfo.short_description = "🌐 Get GEO info"


class PPCFilter(SimpleListFilter):
    title = 'Source'  # or use _('country') for translated title
    parameter_name = 'source'

    def lookups(self, request, model_admin):
        mediums = ['From PPC', 'Course Report']
        return [(m, m) for m in mediums]

    def queryset(self, request, queryset):
        if self.value() == 'From PPC':
            return queryset.filter(gclid__isnull=False)
        if self.value() == 'Course Report':
            return queryset.filter(utm_medium='coursereportschoolpage')


@admin.register(FormEntry)
class FormEntryAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    list_display = ('storage_status', 'created_at', 'first_name', 'last_name',
                    'email', 'location', 'course', 'academy', 'country',
                    'city', 'utm_medium', 'utm_url', 'gclid', 'tags')
    list_filter = [
        'storage_status', 'location', 'course', 'deal_status', PPCFilter,
        'tag_objects__tag_type', 'automation_objects__slug', 'utm_medium',
        'country'
    ]
    actions = [
        send_to_ac, get_geoinfo, fetch_more_facebook_info, "export_as_csv"
    ]


def mark_tag_as_strong(modeladmin, request, queryset):
    queryset.update(tag_type='STRONG')


mark_tag_as_strong.short_description = "Mark tags as STRONG"


def mark_tag_as_soft(modeladmin, request, queryset):
    queryset.update(tag_type='SOFT')


mark_tag_as_soft.short_description = "Mark tags as SOFT"


def mark_tag_as_discovery(modeladmin, request, queryset):
    queryset.update(tag_type='DISCOVERY')


mark_tag_as_discovery.short_description = "Mark tags as DISCOVERY"


def mark_tag_as_other(modeladmin, request, queryset):
    queryset.update(tag_type='OTHER')


mark_tag_as_other.short_description = "Mark tags as OTHER"


class CustomTagModelForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CustomTagModelForm, self).__init__(*args, **kwargs)
        if self.instance.ac_academy is not None:
            self.fields['automation'].queryset = Automation.objects.filter(
                ac_academy=self.instance.ac_academy.id)  # or something else


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    form = CustomTagModelForm
    search_fields = ['slug']
    list_display = ('id', 'slug', 'tag_type', 'acp_id', 'subscribers')
    list_filter = ['tag_type', 'ac_academy__academy__slug']
    actions = [
        mark_tag_as_strong, mark_tag_as_soft, mark_tag_as_discovery,
        mark_tag_as_other, "export_as_csv"
    ]


@admin.register(Automation)
class AutomationAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = ['slug', 'name']
    list_display = ('id', 'acp_id', 'slug', 'name', 'status', 'entered',
                    'exited')
    list_filter = ['status', 'ac_academy__academy__slug']
    actions = ["export_as_csv"]


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = ['slug', 'destination']
    list_display = ('id', 'slug', 'hits', 'active', 'destination_status',
                    'destination')
    list_filter = ['destination_status', 'active']
    actions = ["export_as_csv"]


def run_hook(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for hook in queryset.all():
        ac_academy = hook.ac_academy
        client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
        client.execute_action(hook.id)


run_hook.short_description = "Process Hook"


@admin.register(ActiveCampaignWebhook)
class ActiveCampaignWebhookAdmin(admin.ModelAdmin):
    list_display = ('id', 'webhook_type', 'current_status', 'run_at',
                    'initiated_by', 'created_at')
    actions = [run_hook]

    def current_status(self, obj):
        colors = {
            "DONE": "bg-success",
            "ERROR": "bg-error",
            "PENDING": "bg-warning",
        }
        return format_html(
            f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")

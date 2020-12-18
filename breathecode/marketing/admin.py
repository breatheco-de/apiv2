import csv, logging
from django.contrib import admin, messages
from .models import FormEntry, Tag, Automation, ShortLink, ActiveCampaignAcademy
from .actions import (
    register_new_lead, save_get_geolocal, get_facebook_lead_info, test_ac_connection,
    sync_tags, sync_automations,
)
from django.http import HttpResponse
from django.contrib.admin import SimpleListFilter
# Register your models here.

logger = logging.getLogger(__name__)

class ExportCsvMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"

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

@admin.register(ActiveCampaignAcademy)
class ACAcademyAdmin(admin.ModelAdmin, ExportCsvMixin):
    search_fields = ['academy__name', 'academy__slug']
    list_display = ('id', 'academy', 'ac_url', 'sync_status', 'last_interaction_at', 'sync_message')
    list_filter = ['academy__slug','sync_status']
    actions = [test_ac, sync_ac_tags, sync_ac_automations]

def send_to_ac(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entries:
        register_new_lead(entry.toFormData())
send_to_ac.short_description = "⏫ Upload to Active Campaign"

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
    title = 'Source' # or use _('country') for translated title
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
class FormEntryAdmin(admin.ModelAdmin, ExportCsvMixin):
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    list_display = ('storage_status', 'created_at', 'first_name', 'last_name', 'email', 'location', 'course', 'country', 'city', 'utm_medium', 'utm_url', 'gclid', 'tags')
    list_filter = ['storage_status', 'location', 'course', PPCFilter, 'tag_objects__tag_type', 'automation_objects__slug', 'utm_medium']
    actions = [send_to_ac, get_geoinfo, fetch_more_facebook_info, "export_as_csv"]


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

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin, ExportCsvMixin):
    search_fields = ['slug']
    list_display = ('id', 'slug', 'tag_type', 'acp_id', 'subscribers')
    list_filter = ['tag_type']
    actions = [mark_tag_as_strong, mark_tag_as_soft, mark_tag_as_discovery, mark_tag_as_other, "export_as_csv"]

@admin.register(Automation)
class AutomationAdmin(admin.ModelAdmin, ExportCsvMixin):
    search_fields = ['slug', 'name']
    list_display = ('id', 'acp_id', 'slug', 'name', 'status', 'entered', 'exited')
    list_filter = ['status']
    actions = ["export_as_csv"]

@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin, ExportCsvMixin):
    search_fields = ['slug', 'destination']
    list_display = ('id', 'slug', 'hits', 'active', 'destination_status', 'destination')
    list_filter = ['destination_status', 'active']
    actions = ["export_as_csv"]

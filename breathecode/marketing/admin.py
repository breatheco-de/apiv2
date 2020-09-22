from django.contrib import admin
from .models import FormEntry, Tag, Automation
from .actions import register_new_lead
# Register your models here.

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

def send_to_ac(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entires:
        register_new_lead(entry)

send_to_ac.short_description = "Send to Active Campaign"

@admin.register(FormEntry)
class FormEntryAdmin(admin.ModelAdmin, ExportCsvMixin):
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    list_display = ('storage_status', 'created_at', 'first_name', 'last_name', 'email', 'location', 'course', 'utm_url')
    list_filter = ['storage_status', 'tag_objects__tag_type', 'automation_objects__slug']
    actions = [send_to_ac]


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
    actions = [mark_tag_as_strong, mark_tag_as_soft, mark_tag_as_discovery, mark_tag_as_other]

@admin.register(Automation)
class AutomationAdmin(admin.ModelAdmin, ExportCsvMixin):
    search_fields = ['slug', 'name']
    list_display = ('id', 'acp_id', 'slug', 'name', 'status', 'entered', 'exited')
    list_filter = ['status']

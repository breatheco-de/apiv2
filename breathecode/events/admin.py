import csv
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from .models import Event, Venue, EventType, EventCheckin, Organizacion
from .actions import sync_org_venues

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

def pull_eventbrite_venues(modeladmin, request, queryset):
    entries = queryset.all()

    try:
        for entry in entries:
            sync_org_venues(entry)
    except Exception as e:
        messages.error(request,str(e))

@admin.register(Organizacion)
class OrgAdmin(admin.ModelAdmin):
    list_display = ('name', 'academy', 'eventbrite_id')
    actions = [pull_eventbrite_venues]

# Register your models here.
@admin.register(Event)
class EventAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('slug', 'title', 'url')
    actions = ["export_as_csv"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["queryset"] = User.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# Register your models here.
@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('title', 'city', 'street_address')

# Register your models here.
@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')

# Register your models here.
@admin.register(EventCheckin)
class EventCheckinAdmin(admin.ModelAdmin):
    list_display = ('event', 'attendee', 'created_at')
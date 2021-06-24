from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Event, Venue, EventType, EventCheckin, Organization, Organizer, EventbriteWebhook
from .actions import sync_org_venues, sync_org_events
from breathecode.utils import AdminExportCsvMixin


def pull_eventbrite_venues(modeladmin, request, queryset):
    entries = queryset.all()

    try:
        for entry in entries:
            sync_org_venues(entry)
    except Exception as e:
        print("error", str(e))
        messages.error(request,
                       f"There was an error retriving the venues {str(e)}")


def pull_eventbrite_events(modeladmin, request, queryset):
    entries = queryset.all()

    # try:
    for entry in entries:
        sync_org_events(entry)
    # except Exception as e:
    # print("error", str(e))
    # messages.error(request,f"There was an error retriving the venues {str(e)}")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'academy', 'eventbrite_id')
    actions = [pull_eventbrite_venues, pull_eventbrite_events]


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ('name', 'academy', 'eventbrite_id', 'organization')
    actions = []


# Register your models here.
@admin.register(Event)
class EventAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    search_fields = ['title']
    list_display = ('sync_status', 'title', 'eventbrite_status', 'starting_at',
                    'ending_at', 'sync_desc')
    list_filter = ['eventbrite_status', 'sync_status']
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
    list_display = ('email', 'attendee', 'event', 'status', 'created_at')


@admin.register(EventbriteWebhook)
class EventbriteWebhookAdmin(admin.ModelAdmin):
    list_display = ('api_url', 'user_id', 'action', 'webhook_id',
                    'organization_id', 'endpoint_url', 'status', 'status_text',
                    'created_at')

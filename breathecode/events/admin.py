from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Event, Venue, EventType, EventCheckin, Organization, Organizer, EventbriteWebhook
from .actions import sync_org_venues, sync_org_events
from breathecode.utils import AdminExportCsvMixin
import breathecode.marketing.tasks as marketing_tasks


def pull_eventbrite_venues(modeladmin, request, queryset):
    entries = queryset.all()

    try:
        for entry in entries:
            sync_org_venues(entry)
    except Exception as e:
        print('error', str(e))
        messages.error(request, f'There was an error retriving the venues {str(e)}')


def pull_eventbrite_events(modeladmin, request, queryset):
    entries = queryset.all()

    for entry in entries:
        sync_org_events(entry)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'eventbrite_id', 'sync_status', 'sync_desc', 'academy')
    list_filter = ['sync_status', 'academy']
    search_fields = ['name', 'eventbrite_id']
    actions = [pull_eventbrite_venues, pull_eventbrite_events]


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ('name', 'eventbrite_id', 'academy', 'organization')
    list_filter = ['academy', 'organization']
    search_fields = ['name', 'eventbrite_id']
    actions = []


def reattempt_add_event_slug_as_acp_tag(modeladmin, request, queryset):
    for instance in queryset:
        if instance.academy:
            marketing_tasks.add_event_slug_as_acp_tag.delay(instance.id, instance.academy.id, force=True)


reattempt_add_event_slug_as_acp_tag.short_description = 'Reattempt add event slug to Active Campaign'


# Register your models here.
@admin.register(Event)
class EventAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    list_display = ('slug', 'eventbrite_sync_status', 'title', 'eventbrite_status', 'starting_at',
                    'ending_at', 'eventbrite_sync_description', 'sync_with_eventbrite')
    list_filter = [
        'eventbrite_status', 'eventbrite_sync_status', 'sync_with_eventbrite', 'currency', 'lang', 'academy',
        'organization', 'online_event', 'event_type', 'status'
    ]
    search_fields = ['slug', 'title', 'eventbrite_id', 'eventbrite_organizer_id']
    actions = ['export_as_csv', reattempt_add_event_slug_as_acp_tag]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'author':
            kwargs['queryset'] = User.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def organizer(self, obj):
        return Organizer.objects.filter(eventbrite_id=obj.eventbrite_organizer_id).first()


# Register your models here.
@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('title', 'country', 'state', 'city', 'street_address', 'academy', 'organization')
    list_filter = ['academy', 'organization']
    search_fields = ['title', 'eventbrite_id', 'country', 'state', 'city', 'street_address']


# Register your models here.
@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name', 'academy')
    list_filter = ['academy']
    search_fields = ['slug', 'name']


# Register your models here.
@admin.register(EventCheckin)
class EventCheckinAdmin(admin.ModelAdmin):
    list_display = ('email', 'attendee', 'event', 'status', 'created_at', 'attended_at')
    list_filter = ['status']
    search_fields = ['email', 'event__title', 'event__slug']


@admin.register(EventbriteWebhook)
class EventbriteWebhookAdmin(admin.ModelAdmin):
    list_display = ('api_url', 'user_id', 'action', 'webhook_id', 'organization', 'endpoint_url', 'status',
                    'status_text', 'created_at')
    list_filter = ['organization_id', 'status', 'action']
    search_fields = ['organization_id', 'status']

    def organization(self, obj):
        return Organization.objects.filter(eventbrite_id=obj.organization_id).first()

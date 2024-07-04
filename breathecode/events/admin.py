from datetime import timedelta
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.html import format_html
import breathecode.events.tasks as tasks
from .models import (
    Event,
    EventTypeVisibilitySetting,
    LiveClass,
    Venue,
    EventType,
    EventCheckin,
    Organization,
    Organizer,
    EventbriteWebhook,
)
from .actions import sync_org_venues, sync_org_events
from breathecode.utils import AdminExportCsvMixin
import breathecode.marketing.tasks as marketing_tasks


def pull_eventbrite_venues(modeladmin, request, queryset):
    entries = queryset.all()

    try:
        for entry in entries:
            sync_org_venues(entry)
    except Exception as e:
        print("error", str(e))
        messages.error(request, f"There was an error retriving the venues {str(e)}")


def pull_eventbrite_events(modeladmin, request, queryset):
    entries = queryset.all()

    for entry in entries:
        sync_org_events(entry)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "eventbrite_id", "sync_status", "sync_desc", "academy")
    list_filter = ["sync_status", "academy"]
    search_fields = ["name", "eventbrite_id"]
    actions = [pull_eventbrite_venues, pull_eventbrite_events]


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ("name", "eventbrite_id", "academy", "organization")
    list_filter = ["academy", "organization"]
    search_fields = ["name", "eventbrite_id"]
    actions = []


@admin.display(description="Reattempt add event slug to Active Campaign")
def reattempt_add_event_slug_as_acp_tag(modeladmin, request, queryset):
    for instance in queryset:
        if instance.academy:
            marketing_tasks.add_event_slug_as_acp_tag.delay(instance.id, instance.academy.id, force=True)


# Register your models here.
@admin.register(Event)
class EventAdmin(admin.ModelAdmin, AdminExportCsvMixin):
    list_display = (
        "slug",
        "eventbrite_sync_status",
        "title",
        "status",
        "eventbrite_status",
        "starting_at",
        "ending_at",
        "eventbrite_sync_description",
        "sync_with_eventbrite",
    )
    list_filter = [
        "status",
        "eventbrite_status",
        "eventbrite_sync_status",
        "sync_with_eventbrite",
        "currency",
        "lang",
        "academy",
        "organization",
        "online_event",
        "event_type",
    ]
    search_fields = ["slug", "title", "eventbrite_id", "eventbrite_organizer_id"]
    raw_id_fields = ["host_user"]
    actions = ["export_as_csv", reattempt_add_event_slug_as_acp_tag]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["queryset"] = User.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def organizer(self, obj):
        return Organizer.objects.filter(eventbrite_id=obj.eventbrite_organizer_id).first()


# Register your models here.
@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("title", "country", "state", "city", "street_address", "academy", "organization")
    list_filter = ["academy", "organization"]
    search_fields = ["title", "eventbrite_id", "country", "state", "city", "street_address"]


# Register your models here.
@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "academy")
    list_filter = ["academy"]
    search_fields = ["slug", "name"]
    raw_id_fields = ["academy"]


# Register your models here.
@admin.register(EventCheckin)
class EventCheckinAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "attendee", "event", "status", "created_at", "attended_at", "utm_source")
    list_filter = ["status", "utm_source", "utm_medium"]
    search_fields = ["email", "event__title", "event__slug"]
    raw_id_fields = ["event", "attendee"]


def reattempt_eventbrite_webhook(modeladmin, request, queryset):
    entries = queryset.all()

    for entry in entries:
        tasks.async_eventbrite_webhook.delay(entry.id)


@admin.register(EventbriteWebhook)
class EventbriteWebhookAdmin(admin.ModelAdmin):
    list_display = ("id", "current_status", "action", "organization", "user_attendee", "event", "created_at")
    list_filter = ["organization_id", "status", "action"]
    search_fields = [
        "organization_id",
        "status",
        "event__title",
        "event__slug",
        "attendee__email",
        "attendee__first_name",
        "attendee__last_name",
        "event__uuid",
    ]
    raw_id_fields = ["event", "attendee"]
    actions = [reattempt_eventbrite_webhook]

    def organization(self, obj):
        return Organization.objects.filter(eventbrite_id=obj.organization_id).first()

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

    def user_attendee(self, obj):
        if obj.attendee is None:
            return "-"
        return format_html(f"<a href='/admin/auth/user/{obj.attendee.id}/change/'>{str(obj.attendee)}</a>")


@admin.register(EventTypeVisibilitySetting)
class EventTypeVisibilitySettingAdmin(admin.ModelAdmin):
    list_display = ("academy", "cohort", "syllabus")
    list_filter = ["academy"]
    search_fields = [
        "academy__slug",
        "academy__name",
        "syllabus__slug",
        "syllabus__name",
        "cohort__slug",
        "cohort__name",
    ]
    actions = [reattempt_eventbrite_webhook]
    raw_id_fields = ["syllabus", "cohort", "academy"]


@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = (
        "cohort_time_slot",
        "remote_meeting_url",
        "starting_at",
        "ending_at",
        "started_at",
        "ended_at",
        "did_it_close_automatically",
    )
    list_filter = ["cohort_time_slot__recurrent", "cohort_time_slot__recurrency_type"]
    search_fields = ["id", "remote_meeting_url"]

    def did_it_close_automatically(self, obj: LiveClass):
        if not obj.ended_at:
            return False

        return obj.ending_at + timedelta(minutes=30) == obj.ended_at

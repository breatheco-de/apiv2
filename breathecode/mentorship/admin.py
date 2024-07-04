import pytz, logging, requests, re
from django.contrib import admin, messages
from django import forms
from .models import (
    MentorProfile,
    MentorshipService,
    MentorshipSession,
    MentorshipBill,
    SupportAgent,
    SupportChannel,
    ChatBot,
    CalendlyOrganization,
    CalendlyWebhook,
)
from breathecode.services.calendly import Calendly
from django.utils.html import format_html
import breathecode.mentorship.tasks as tasks
from breathecode.utils.admin import change_field
from django.contrib.admin import SimpleListFilter
import breathecode.mentorship.actions as actions

timezones = [(x, x) for x in pytz.common_timezones]
logger = logging.getLogger(__name__)


@admin.register(MentorshipService)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "status", "academy"]
    search_fields = ["slug", "name"]
    list_filter = ["academy__slug", "status"]
    # raw_id_fields = ['academy', 'github_user']
    # actions = [sync_issues, generate_bill]

    # def full_name(self, obj):
    #     return obj.user.first_name + ' ' + obj.user.last_name


class MentorForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(MentorForm, self).__init__(*args, **kwargs)
        self.fields["timezone"] = forms.ChoiceField(choices=timezones)


def generate_bill(modeladmin, request, queryset):
    mentors = queryset.all()
    for m in mentors:
        actions.generate_mentor_bills(m, reset=True)


def mark_as_active(modeladmin, request, queryset):
    if not queryset:
        return

    entries = queryset.all()
    connection_errors = []
    exceptions = {}

    connection_error_message = "Booking or meeting URL for mentor is failing ({})"

    for entry in entries:
        try:
            actions.mentor_is_ready(entry)

        except requests.exceptions.ConnectionError:
            message = "Error: Booking or meeting URL for mentor is failing"
            logger.fatal(message)
            connection_errors.append(entry.slug)

        except Exception as e:
            error = str(e)
            logger.fatal(error)

            if error not in exceptions:
                exceptions[error] = [entry.slug]
            else:
                exceptions[error].append(entry.slug)

    if connection_errors and exceptions:
        all_errors = "Error:"

        all_errors = f'{all_errors} {connection_error_message.format(", ".join(connection_errors))}.'

        for error, slugs in exceptions.items():
            all_errors = f'{all_errors} {error} ({", ".join(slugs)}).'

        messages.error(request, all_errors)
        return

    if connection_errors:
        messages.error(request, f'Error: {connection_error_message.format(", ".join(connection_errors))}.')

    if exceptions:
        all_errors = "Error:"

        for error, slugs in exceptions.items():
            all_errors = f'{all_errors} {error} ({", ".join(slugs)}).'

        messages.error(request, all_errors)

    if not connection_errors and not exceptions:
        messages.success(request, "Mentor updated successfully")


def generate_slug_based_on_calendly(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entries:

        if entry.booking_url is None:
            messages.error(request, f"Mentor {entry.id} has no booking url")
            continue

        result = re.search(r"^https?:\/\/calendly.com\/([\w\-]+)\/?.*", entry.booking_url)
        if result is None:
            messages.error(request, f"Mentor {entry.id} booking url is not calendly: {entry.booking_url}")
            continue

        calendly_username = result.group(1)
        entry.slug = calendly_username
        entry.save()


@admin.register(SupportChannel)
class SupportChannelAdmin(admin.ModelAdmin):
    list_display = ["id", "slug", "slack_channel", "academy"]
    raw_id_fields = ["slack_channel", "academy", "syllabis"]
    search_fields = ["slug", "slack_channel__slack_id", "slack_channel__name"]
    list_filter = ["syllabis"]


@admin.register(SupportAgent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "channel", "email", "current_status"]
    raw_id_fields = ["user", "channel"]
    search_fields = ["email", "user__first_name", "user__last_name", "user__email"]
    list_filter = ["channel__academy__slug", "status", "channel__syllabis__slug", "channel__slug"]
    readonly_fields = ("token",)
    actions = change_field(["INNACTIVE", "INVITED"], name="status")

    def current_status(self, obj):
        colors = {
            "ACTIVE": "bg-success",
            "INVITED": "bg-warning",
            "UNLISTED": "bg-warning",
            "INNACTIVE": "bg-error",
            None: "bg-warning",
        }

        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")


@admin.register(MentorProfile)
class MentorAdmin(admin.ModelAdmin):
    form = MentorForm
    list_display = ["slug", "user", "name", "email", "current_status", "unique_url", "meet_url", "academy"]
    raw_id_fields = ["user", "services"]
    search_fields = ["name", "user__first_name", "user__last_name", "email", "user__email", "slug"]
    list_filter = ["services__academy__slug", "status", "services__slug"]
    readonly_fields = ("token",)
    filter_horizontal = ("syllabus", "services")
    actions = [generate_bill, mark_as_active, generate_slug_based_on_calendly] + change_field(
        ["INNACTIVE", "INVITED"], name="status"
    )

    def current_status(self, obj):
        colors = {
            "ACTIVE": "bg-success",
            "INVITED": "bg-warning",
            "UNLISTED": "bg-warning",
            "INNACTIVE": "bg-error",
            None: "bg-warning",
        }

        if obj.online_meeting_url is None:
            return format_html("<span class='badge bg-error'> Missing Meeting URL</span>")

        if obj.booking_url is None:
            return format_html("<span class='badge bg-error'> Missing Booking URL</span>")

        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")

    def unique_url(self, obj):
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='/mentor/{obj.slug}'>book</a>")

    def meet_url(self, obj):
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='/mentor/meet/{obj.slug}'>meet</a>")


def avoid_billing_this_session(modeladmin, request, queryset):
    queryset.update(allow_billing=False)


def allow_billing_this_session(modeladmin, request, queryset):
    queryset.update(allow_billing=True)


class BilledFilter(SimpleListFilter):
    title = "billed"
    parameter_name = "billed"

    def lookups(self, request, model_admin):
        return [
            ("false", "Not yet billed"),
            ("true", "Already billed"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "false":
            return queryset.filter(bill__isnull=True)
        if self.value():
            return queryset.filter(bill__isnull=False)


@admin.register(MentorshipSession)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["id", "mentor", "mentee", "stats", "started_at", "mentor_joined_at", "openurl"]
    raw_id_fields = ["mentor", "mentee"]
    search_fields = [
        "mentee__first_name",
        "mentee__last_name",
        "mentee__email",
        "mentor__user__first_name",
        "mentor__user__last_name",
        "mentor__user__email",
    ]
    list_filter = [BilledFilter, "allow_billing", "status", "mentor__services__academy", "mentor__services__slug"]
    actions = [avoid_billing_this_session, allow_billing_this_session] + change_field(
        ["COMPLETED", "FAILED", "STARTED", "PENDING"], name="status"
    )

    def stats(self, obj):

        colors = {
            "COMPLETED": "bg-success",
            "FAILED": "bg-error",
            "STARTED": "bg-warning",
            "PENDING": "bg-secondary",
            "CANCELED": "",
            "IGNORED": "bg-secondary",
        }

        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")

    def openurl(self, obj):
        url = obj.online_meeting_url
        if url is None:
            url = obj.mentor.online_meeting_url

        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='/mentor/meet/{obj.mentor.slug}?session={str(obj.id)}'>open</a>"
        )


def release_sessions_from_bill(modeladmin, request, queryset):
    bills = queryset.all()
    for b in bills:
        b.total_price = 0
        b.total_duration_in_hours = 0
        b.total_duration_in_minutes = 0
        b.overtime_minutes = 0
        for session in b.mentorshipsession_set.all():
            session.bill = None
            session.accounted_duration = None
            session.save()
        b.save()


@admin.register(MentorshipBill)
class MentorshipBillAdmin(admin.ModelAdmin):
    list_display = ("id", "mentor", "status", "total_duration_in_hours", "total_price", "paid_at", "invoice_url")
    list_filter = ["status"]
    actions = [release_sessions_from_bill] + change_field(["DUE", "APPROVED", "PAID", "IGNORED"], name="status")

    def invoice_url(self, obj):
        return format_html(
            "<a rel='noopener noreferrer' target='_blank' href='/v1/mentorship/academy/bill/{id}/html'>open</a>",
            id=obj.id,
        )


@admin.register(ChatBot)
class ChatBotAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "academy")
    list_filter = ["academy"]
    # actions = [release_sessions_from_bill] + change_field(['DUE', 'APPROVED', 'PAID', 'IGNORED'],
    #                                                       name='status')


def subscribe_to_webhooks(modeladmin, request, queryset):
    entries = queryset.all()
    for org in entries:
        cal = Calendly(token=org.access_token)
        cal.subscribe(org.uri, org.hash)


def unsubscribe_to_all_webhooks(modeladmin, request, queryset):
    entries = queryset.all()
    for org in entries:
        cal = Calendly(token=org.access_token)
        cal.unsubscribe_all(org.uri)


def get_subscription_webhooks(modeladmin, request, queryset):
    entries = queryset.all()
    for org in entries:
        cal = Calendly(token=org.access_token)
        data = cal.get_subscriptions(org.uri)
        print("subscriptions", data)


@admin.register(CalendlyOrganization)
class CalendlyOrganizationAdmin(admin.ModelAdmin):
    list_display = ("username", "academy", "hash", "sync_status", "sync_desc")
    list_filter = ["sync_status", "academy"]
    search_fields = ["username"]
    readonly_fields = ("hash",)
    actions = [subscribe_to_webhooks, get_subscription_webhooks, unsubscribe_to_all_webhooks]


def reattempt_calendly_webhook(modeladmin, request, queryset):
    entries = queryset.all()

    for entry in entries:
        tasks.async_calendly_webhook.delay(entry.id)


@admin.register(CalendlyWebhook)
class CalendlyWebhookAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "event",
        "organization",
        "organization_hash",
        "created_by",
        "status_text",
        "created_at",
    )
    list_filter = ["organization", "status", "event"]
    search_fields = ["organization__username"]
    actions = [reattempt_calendly_webhook]

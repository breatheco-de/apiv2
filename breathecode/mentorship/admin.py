import json, pytz, logging, requests, re
from django.contrib import admin, messages
from django import forms
from .models import MentorProfile, MentorshipService, MentorshipSession, MentorshipBill
from .actions import generate_mentor_bills, mentor_is_ready
from django.utils.html import format_html
from breathecode.utils.admin import change_field
from django.contrib.admin import SimpleListFilter

timezones = [(x, x) for x in pytz.common_timezones]
logger = logging.getLogger(__name__)


@admin.register(MentorshipService)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['slug', 'name', 'status', 'academy']
    search_fields = ['slug', 'name']
    list_filter = ['academy__slug', 'status']
    # raw_id_fields = ['academy', 'github_user']
    # actions = [sync_issues, generate_bill]

    # def full_name(self, obj):
    #     return obj.user.first_name + ' ' + obj.user.last_name


class MentorForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(MentorForm, self).__init__(*args, **kwargs)
        self.fields['timezone'] = forms.ChoiceField(choices=timezones)


def generate_bill(modeladmin, request, queryset):
    mentors = queryset.all()
    for m in mentors:
        generate_mentor_bills(m, reset=True)


def mark_as_active(modeladmin, request, queryset):
    entries = queryset.all()
    try:
        for entry in entries:
            mentor_is_ready(entry)

        messages.success(request, message='Mentor updated successfully')
    except requests.exceptions.ConnectionError:
        message = 'Error: Booking or meeting URL for mentor is failing'
        logger.fatal(message)
        messages.error(request, message)
    except Exception as e:
        logger.fatal(str(e))
        messages.error(request, 'Error: ' + str(e))


def generate_slug_based_on_calendly(modeladmin, request, queryset):
    entries = queryset.all()
    for entry in entries:

        if entry.booking_url is None:
            messages.error(request, f'Mentor {entry.id} has no booking url')
            continue

        result = re.search(r'^https?:\/\/calendly.com\/([\w\-]+)\/?.*', entry.booking_url)
        if result is None:
            messages.error(request, f'Mentor {entry.id} booking url is not calendly: {entry.booking_url}')
            continue

        calendly_username = result.group(1)
        entry.slug = calendly_username
        entry.save()


@admin.register(MentorProfile)
class MentorAdmin(admin.ModelAdmin):
    form = MentorForm
    list_display = ['slug', 'user', 'name', 'email', 'current_status', 'unique_url', 'meet_url']
    raw_id_fields = ['user', 'service']
    search_fields = ['name', 'user__first_name', 'user__last_name', 'email', 'user__email']
    list_filter = ['service__academy__slug', 'status', 'service__slug']
    readonly_fields = ('token', )
    actions = [generate_bill, mark_as_active, generate_slug_based_on_calendly] + change_field(
        ['INNACTIVE', 'INVITED'], name='status')

    def current_status(self, obj):
        colors = {
            'ACTIVE': 'bg-success',
            'INVITED': 'bg-warning',
            'UNLISTED': 'bg-warning',
            'INNACTIVE': 'bg-error',
            None: 'bg-warning',
        }

        if obj.online_meeting_url is None:
            return format_html(f"<span class='badge bg-error'> Missing Meeting URL</span>")

        if obj.booking_url is None:
            return format_html(f"<span class='badge bg-error'> Missing Booking URL</span>")

        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")

    def unique_url(self, obj):
        return format_html(f"<a rel='noopener noreferrer' target='_blank' href='/mentor/{obj.slug}'>book</a>")

    def meet_url(self, obj):
        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='/mentor/meet/{obj.slug}'>meet</a>")


def avoid_billing_this_session(modeladmin, request, queryset):
    sessions = queryset.update(allow_billing=False)


def allow_billing_this_session(modeladmin, request, queryset):
    sessions = queryset.update(allow_billing=True)


class BilledFilter(SimpleListFilter):
    title = 'billed'
    parameter_name = 'billed'

    def lookups(self, request, model_admin):
        return [
            ('false', 'Not yet billed'),
            ('true', 'Already billed'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'false':
            return queryset.filter(bill__isnull=True)
        if self.value():
            return queryset.filter(bill__isnull=False)


@admin.register(MentorshipSession)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'mentor', 'mentee', 'stats', 'started_at', 'mentor_joined_at', 'openurl']
    raw_id_fields = ['mentor', 'mentee']
    search_fields = [
        'mentee__first_name', 'mentee__last_name', 'mentee__email', 'mentor__user__first_name',
        'mentor__user__last_name', 'mentor__user__email'
    ]
    list_filter = [
        BilledFilter, 'allow_billing', 'status', 'mentor__service__academy', 'mentor__service__slug'
    ]
    actions = [avoid_billing_this_session, allow_billing_this_session] + change_field(
        ['COMPLETED', 'FAILED', 'STARTED', 'PENDING'], name='status')

    def stats(self, obj):

        colors = {
            'COMPLETED': 'bg-success',
            'FAILED': 'bg-error',
            'STARTED': 'bg-warning',
            'PENDING': 'bg-secondary',
            'IGNORED': 'bg-secondary',
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
    list_display = ('id', 'mentor', 'status', 'total_duration_in_hours', 'total_price', 'paid_at',
                    'invoice_url')
    list_filter = ['status']
    actions = [release_sessions_from_bill] + change_field(['DUE', 'APPROVED', 'PAID', 'IGNORED'],
                                                          name='status')

    def invoice_url(self, obj):
        return format_html(
            "<a rel='noopener noreferrer' target='_blank' href='/v1/mentorship/academy/bill/{id}/html'>open</a>",
            id=obj.id)

import json, pytz
from django.contrib import admin, messages
from django import forms
from .models import MentorProfile, MentorshipService, MentorshipSession
from django.utils.html import format_html

timezones = [(x, x) for x in pytz.common_timezones]


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


@admin.register(MentorProfile)
class MentorAdmin(admin.ModelAdmin):
    form = MentorForm
    list_display = ['slug', 'user', 'name', 'email', 'current_status', 'unique_url', 'meet_url']
    raw_id_fields = ['user', 'service']
    search_fields = ['name', 'user__first_name', 'user__last_name', 'email', 'user__email']
    list_filter = ['service__academy__slug', 'status', 'service__slug']
    readonly_fields = ('token', )

    def current_status(self, obj):
        colors = {
            'ACTIVE': 'bg-success',
            'INVITED': 'bg-warning',
            'INNACTIVE': 'bg-warning',
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


@admin.register(MentorshipSession)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'mentor', 'mentee', 'status', 'started_at', 'openurl']
    raw_id_fields = ['mentor', 'mentee']
    search_fields = [
        'mentee__first_name', 'mentee__last_name', 'mentee__email', 'mentor__user__first_name',
        'mentor__user__last_name', 'mentor__user__email'
    ]
    list_filter = ['mentor__service__academy', 'status', 'mentor__service__slug']

    def openurl(self, obj):
        url = obj.online_meeting_url
        if url is None:
            url = obj.mentor.online_meeting_url

        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='/mentor/meet/{obj.mentor.slug}'>open</a>")

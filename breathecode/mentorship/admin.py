import json
from django.contrib import admin, messages
from .models import MentorProfile, MentorshipService, MentorshipSession
from django.utils.html import format_html


@admin.register(MentorshipService)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['slug', 'name', 'status', 'academy']
    search_fields = ['slug', 'name']
    list_filter = ['academy__slug', 'status']
    # raw_id_fields = ['academy', 'github_user']
    # actions = [sync_issues, generate_bill]

    # def full_name(self, obj):
    #     return obj.user.first_name + ' ' + obj.user.last_name


@admin.register(MentorProfile)
class MentorAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'email', 'status', 'unique_url']
    raw_id_fields = ['user', 'service']
    search_fields = ['name', 'user__first_name', 'user__last_name', 'email', 'user__email']
    list_filter = ['service__academy__slug', 'status', 'service__slug']

    def unique_url(self, request):
        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='/v1/mentorhip/meet/{self.slug}'>book with {self.slug}</a>"
        )


@admin.register(MentorshipSession)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'mentor', 'mentee', 'status', 'started_at', 'openurl']
    raw_id_fields = ['mentor', 'mentee']
    search_fields = [
        'mentee__first_name', 'mentee__last_name', 'mentee__email', 'mentor__user__first_name',
        'mentor__user__last_name', 'mentor__user__email'
    ]
    list_filter = ['mentor__service__academy', 'status', 'mentor__service__slug']

    def openurl(self, request):
        url = self.online_meeting_url
        if url is None:
            url = self.mentor.online_meeting_url

        return format_html(
            f"<a rel='noopener noreferrer' target='_blank' href='/v1/mentorhip/meet/{self.slug}'>open {url}</a>"
        )

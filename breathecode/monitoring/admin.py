from django.contrib import admin
from django import forms 
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Endpoint, Application
from breathecode.notify.models import SlackChannel
from breathecode.notify.actions import send_slack_raw
from django.utils.html import format_html
from .actions import get_website_text, run_app_diagnostic
from breathecode.notify.actions import send_email_message

def test_app(modeladmin, request, queryset):
    appications = queryset.all()
    for app in appications:
        result = run_app_diagnostic(app)
        if result["status"] != "OPERATIONAL" and app.notify_slack_channel is not None:
            send_slack_raw("diagnostic", app.academy.slackteam.owner.credentialsslack.token, app.notify_slack_channel.slack_id, {
                "subject": f"Errors have been found on {app.title} diagnostic",
                **result,
            })
test_app.short_description = "Run Applications Diagnostic"

class CustomAppModelForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CustomAppModelForm, self).__init__(*args, **kwargs)
        if hasattr(self.instance, 'academy') and self.instance.academy is not None:
            self.fields['notify_slack_channel'].queryset = SlackChannel.objects.filter(team__academy__id=self.instance.academy.id)# or something else

# Register your models here.
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    form = CustomAppModelForm
    list_display = ('title', 'current_status', 'academy', 'paused_until', 'status_text')
    actions=[test_app]
    list_filter = ['status', 'academy__slug']

    def current_status(self,obj):
        colors = {
            "OPERATIONAL": "bg-success",
            "CRITICAL": "bg-error",
            "MINOR": "bg-warning",
        }
        now = timezone.now()
        if obj.paused_until is not None and obj.paused_until > now:
            return format_html(f"<span class='badge bc-warning'> ⏸ PAUSED</a>")

        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</a>")

def test_endpoint(modeladmin, request, queryset):
    endpoints = queryset.all()
    for end in endpoints:
        get_website_text(end)
test_endpoint.short_description = "Test Endpoint"

# Register your models here.
@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = ('url', 'current_status', 'test_pattern', 'status_code', 'paused_until', 'last_check')
    actions=[test_endpoint]
    list_filter = ['status','application__title']
    
    def current_status(self,obj):
        colors = {
            "OPERATIONAL": "bg-success",
            "CRITICAL": "bg-error",
            "MINOR": "bg-warning",
        }
        now = timezone.now()
        if obj.paused_until is not None and obj.paused_until > now:
            return format_html(f"<span class='badge bc-warning'> ⏸ PAUSED</a>")

        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</a>")
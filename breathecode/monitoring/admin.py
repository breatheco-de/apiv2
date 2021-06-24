import os, ast
from django.contrib import admin
from django import forms
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Endpoint, Application, MonitorScript
from breathecode.notify.models import SlackChannel
from django.utils.html import format_html


def test_app(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    from .tasks import monitor_app

    for app in queryset.all():
        monitor_app.delay(app.id)


test_app.short_description = "Run Applications Diagnostic"


class CustomAppModelForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CustomAppModelForm, self).__init__(*args, **kwargs)
        if hasattr(self.instance,
                   'academy') and self.instance.academy is not None:
            self.fields[
                'notify_slack_channel'].queryset = SlackChannel.objects.filter(
                    team__academy__id=self.instance.academy.id
                )  # or something else


# Register your models here.
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    form = CustomAppModelForm
    list_display = ('title', 'current_status', 'academy', 'paused_until',
                    'status_text')
    actions = [test_app]
    list_filter = ['status', 'academy__slug']
    raw_id_fields = ["notify_slack_channel"]

    def current_status(self, obj):
        colors = {
            "OPERATIONAL": "bg-success",
            "CRITICAL": "bg-error",
            "MINOR": "bg-warning",
        }
        now = timezone.now()
        if obj.paused_until is not None and obj.paused_until > now:
            return format_html(
                f"<span class='badge bc-warning'> ⏸ PAUSED</span>")

        return format_html(
            f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")


def test_endpoint(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    from .tasks import test_endpoint

    for end in queryset.all():
        test_endpoint.delay(end.id)


test_endpoint.short_description = "Test Endpoint"


def pause_for_one_day(modeladmin, request, queryset):
    for end in queryset.all():
        end.paused_until = timezone.now() + timezone.timedelta(days=1)
        end.save()


pause_for_one_day.short_description = "PAUSE for 1 day"


# Register your models here.
@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = ('url', 'current_status', 'test_pattern', 'status_code',
                    'paused_until', 'last_check')
    actions = [test_endpoint, pause_for_one_day]
    list_filter = ['status', 'application__title']

    def get_readonly_fields(self, request, obj=None):
        return ['status_text']

    def current_status(self, obj):
        colors = {
            "OPERATIONAL": "bg-success",
            "CRITICAL": "bg-error",
            "MINOR": "bg-warning",
        }
        now = timezone.now()
        if obj.paused_until is not None and obj.paused_until > now:
            return format_html(
                f"<span class='badge bc-warning'> ⏸ PAUSED</span>")

        return format_html(
            f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")


def run_single_script(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    from .tasks import execute_scripts

    for s in queryset.all():
        execute_scripts.delay(s.id)


run_single_script.short_description = "Run Script"


class CustomForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(CustomForm, self).__init__(*args, **kwargs)

        options = []
        dir_path = os.path.dirname(os.path.realpath(__file__))
        files = os.listdir(dir_path + "/scripts")
        for file_name in files:
            if ".py" not in file_name:
                continue
            doc = file_name
            with open(dir_path + "/scripts/" + file_name) as f:
                doc = ast.get_docstring(ast.parse(f.read()))
            options.append((file_name[0:-3], doc))
        options.append(("other", "other"))

        # timezones = [(x, x) for x in pytz.common_timezones]
        self.fields['script_slug'] = forms.ChoiceField(choices=options)


@admin.register(MonitorScript)
class MonitorScriptAdmin(admin.ModelAdmin):
    form = CustomForm
    list_display = ('script_slug', 'application', 'current_status',
                    'frequency_delta', 'status_code', 'paused_until',
                    'last_run')
    actions = [run_single_script]
    list_filter = ['status', 'application__title']

    def current_status(self, obj):
        colors = {
            "OPERATIONAL": "bg-success",
            "CRITICAL": "bg-error",
            "MINOR": "bg-warning",
        }
        now = timezone.now()
        if obj.paused_until is not None and obj.paused_until > now:
            return format_html(
                f"<span class='badge bc-warning'> ⏸ PAUSED</span>")

        return format_html(
            f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")

import os, ast
from django.contrib import admin
from django import forms
from django.utils import timezone
from .signals import github_webhook
from .tasks import async_unsubscribe_repo, async_subscribe_repo
from .actions import unsubscribe_repository, subscribe_repository
from .models import Endpoint, Application, MonitorScript, CSVDownload, CSVUpload, RepositoryWebhook, RepositorySubscription
from breathecode.notify.models import SlackChannel
from django.utils.html import format_html


@admin.display(description='Run Applications Diagnostic')
def test_app(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    from .tasks import monitor_app

    for app in queryset.all():
        monitor_app.delay(app.id)


class CustomAppModelForm(forms.ModelForm):

    class Meta:
        model = Application
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CustomAppModelForm, self).__init__(*args, **kwargs)
        if hasattr(self.instance, 'academy') and self.instance.academy is not None:
            self.fields['notify_slack_channel'].queryset = SlackChannel.objects.filter(
                team__academy__id=self.instance.academy.id)  # or something else


# Register your models here.
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    form = CustomAppModelForm
    list_display = ('title', 'current_status', 'academy', 'paused_until', 'status_text')
    actions = [test_app]
    list_filter = ['status', 'academy__slug']
    raw_id_fields = ['notify_slack_channel']

    def current_status(self, obj):
        colors = {
            'OPERATIONAL': 'bg-success',
            'CRITICAL': 'bg-error',
            'MINOR': 'bg-warning',
            'LOADING': 'bg-warning',
        }
        now = timezone.now()
        if obj.paused_until is not None and obj.paused_until > now:
            return format_html("<span class='badge bc-warning'> ⏸ PAUSED</span>")

        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")


@admin.display(description='Test Endpoint')
def test_endpoint(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    from .tasks import test_endpoint

    for end in queryset.all():
        test_endpoint.delay(end.id)


@admin.display(description='PAUSE for 1 day')
def pause_for_one_day(modeladmin, request, queryset):
    for end in queryset.all():
        end.paused_until = timezone.now() + timezone.timedelta(days=1)
        end.save()


# Register your models here.
@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = ('url', 'current_status', 'test_pattern', 'status_code', 'paused_until', 'last_check')
    actions = [test_endpoint, pause_for_one_day]
    list_filter = ['status', 'application__title']

    def get_readonly_fields(self, request, obj=None):
        return ['status_text']

    def current_status(self, obj):
        colors = {
            'OPERATIONAL': 'bg-success',
            'CRITICAL': 'bg-error',
            'MINOR': 'bg-warning',
        }
        now = timezone.now()
        if obj.paused_until is not None and obj.paused_until > now:
            return format_html("<span class='badge bc-warning'> ⏸ PAUSED</span>")

        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")


@admin.display(description='Run Script')
def run_single_script(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    from .tasks import execute_scripts

    for s in queryset.all():
        execute_scripts.delay(s.id)


class CustomForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(CustomForm, self).__init__(*args, **kwargs)

        options = []
        dir_path = os.path.dirname(os.path.realpath(__file__))
        files = os.listdir(dir_path + '/scripts')
        for file_name in files:
            if '.py' not in file_name:
                continue
            doc = file_name
            with open(dir_path + '/scripts/' + file_name) as f:
                doc = ast.get_docstring(ast.parse(f.read()))
            options.append((file_name[0:-3], doc))
        options.append(('other', 'other'))

        # timezones = [(x, x) for x in pytz.common_timezones]
        self.fields['script_slug'] = forms.ChoiceField(choices=options)


@admin.register(MonitorScript)
class MonitorScriptAdmin(admin.ModelAdmin):
    form = CustomForm
    list_display = ('script_slug', 'application', 'current_status', 'frequency_delta', 'status_code', 'paused_until',
                    'last_run')
    actions = [run_single_script]
    list_filter = ['status', 'application__title']

    def current_status(self, obj):
        colors = {
            'OPERATIONAL': 'bg-success',
            'CRITICAL': 'bg-error',
            'FATAL': 'bg-error',  # important: this status was deprecated and deleted!
            'MINOR': 'bg-warning',
        }
        now = timezone.now()
        if obj.paused_until is not None and obj.paused_until > now:
            return format_html("<span class='badge bc-warning'> ⏸ PAUSED</span>")

        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")


@admin.register(CSVDownload)
class CSVDownloadAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'current_status', 'created_at', 'finished_at', 'download')
    list_filter = ['academy', 'status']

    def current_status(self, obj):
        colors = {
            'DONE': 'bg-success',
            'ERROR': 'bg-error',
            'LOADING': 'bg-warning',
        }
        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")

    def download(self, obj):
        if obj.status == 'DONE':
            return format_html(f"<a href='/v1/monitoring/download/{obj.id}?raw=true' target='_blank'>download</span>")
        return format_html('nothing to download')


@admin.register(CSVUpload)
class CSVUploadAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'status', 'academy', 'hash')
    list_filter = ['academy', 'status']
    search_fields = ['name', 'url', 'hash']


def delete_subscription(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for subs in queryset.all():
        # unsubscribe_repo_subscription(subs.hook_id)
        async_unsubscribe_repo.delay(subs.hook_id, force_delete=True)


def disable_subscription(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for subs in queryset.all():
        if subs.hook_id is not None and subs.hook_id != "": 
            unsubscribe_repository(subs.id, force_delete=False)
        else:
            subs.status = 'DISABLED'
            subs.save()


def activate_subscription(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for subs in queryset.all():
        subscribe_repository(subs.id)


@admin.register(RepositorySubscription)
class RepositorySubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'current_status', 'hook_id', 'repo', 'owner', 'shared')
    list_filter = ['status','owner']
    search_fields = ['repository', 'token','hook_id']
    readonly_fields = ['token']
    actions = [delete_subscription, disable_subscription, activate_subscription]

    def get_actions(self, request):
        actions = super(RepositorySubscriptionAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        # Return False to remove the "Delete" button from the update form.
        # You can add additional logic here if you want to conditionally
        # enable the delete button for certain cases.
        return False

    def repo(self, obj):
        return format_html(f"""
            <a rel='noopener noreferrer' target='_blank' href='{obj.repository}/settings/hooks'>{obj.repository}</a>
        """)

    def shared(self, obj):
        return format_html(''.join([o.name for o in obj.shared_with.all()]))

    def current_status(self, obj):
        colors = {
            'OPERATIONAL': 'bg-success',
            'CRITICAL': 'bg-error',
            'DISABLED': 'bg-warning',
            None: 'bg-warning',
        }
        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")


def process_webhook(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for hook in queryset.all():
        github_webhook.send(instance=hook, sender=RepositoryWebhook)


@admin.register(RepositoryWebhook)
class RepositoryWebhookAdmin(admin.ModelAdmin):
    list_display = ('id', 'webhook_action', 'scope', 'current_status', 'run_at', 'academy_slug', 'created_at')
    list_filter = ['status', 'webhook_action', 'scope', 'academy_slug']
    actions = [process_webhook]

    def current_status(self, obj):
        colors = {
            'DONE': 'bg-success',
            'ERROR': 'bg-error',
            'PENDING': 'bg-warning',
        }
        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")

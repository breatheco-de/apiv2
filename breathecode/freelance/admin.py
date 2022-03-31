import json
from django.contrib import admin, messages
from .models import Freelancer, Issue, Bill, RepositoryIssueWebhook
from django.utils.html import format_html
from . import actions
from breathecode.utils.admin import change_field
from .tasks import async_repository_issue_github
# Register your models here.


def sync_issues(modeladmin, request, queryset):
    freelancers = queryset.all()
    for freelancer in freelancers:
        try:
            actions.sync_user_issues(freelancer)
        except ValueError as err:
            messages.error(request, err)


sync_issues.short_description = 'Sync open issues'


def generate_bill(modeladmin, request, queryset):
    freelancers = queryset.all()
    for freelancer in freelancers:
        try:
            actions.generate_freelancer_bill(freelancer)
        except ValueError as err:
            messages.error(request, err)


generate_bill.short_description = 'Generate bill'


def mark_as(queryset, status, request):
    freelancers = {}
    issues = queryset.all()

    try:
        for i in issues:
            if i.bill is not None and i.bill.status != 'DUE':
                raise Exception(
                    f'Github {i.github_number} cannot be updated because it was already approved for payment')
            freelancers[i.freelancer.id] = i.freelancer
            i.status = status
            i.save()

        for freelancer_id in freelancers:
            actions.generate_freelancer_bill(freelancers[freelancer_id])
    except Exception as e:
        messages.error(request, e)


@admin.register(Freelancer)
class FreelancerAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'full_name', 'email', 'github', 'price_per_hour']
    raw_id_fields = ['user', 'github_user']
    actions = [sync_issues, generate_bill]

    def full_name(self, obj):
        return obj.user.first_name + ' ' + obj.user.last_name

    def email(self, obj):
        return obj.user.email

    def github(self, obj):
        if obj.github_user is None:
            return format_html(f"<span class='badge bg-error'> Missing github connection</span>")

        if obj.price_per_hour == 0 or obj.price_per_hour is None:
            return format_html(f"<span class='badge bg-error'> Missing rate per hour</span>")

        return format_html(f"<span class='badge bg-success'>Connected to Github</span>")


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    search_fields = [
        'title', 'freelancer__user__email', 'freelancer__user__first_name', 'freelancer__user__last_name',
        'github_number'
    ]
    list_display = ('id', 'github_number', 'freelancer', 'title', 'status', 'duration_in_hours', 'bill_id',
                    'github_url')
    list_filter = ['status', 'bill__status']
    actions = change_field(['TODO', 'DONE', 'IGNORED', 'DRAFT', 'DOING'], name='status')

    def github_url(self, obj):
        return format_html("<a rel='noopener noreferrer' target='_blank' href='{url}'>open in github</a>",
                           url=obj.url)


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('id', 'freelancer', 'status', 'total_duration_in_hours', 'total_price', 'paid_at',
                    'invoice_url')
    list_filter = ['status']
    actions = change_field(['PAID', 'APPROVED', 'IGNORED', 'DUE'], name='status')

    def invoice_url(self, obj):
        return format_html(
            "<a rel='noopener noreferrer' target='_blank' href='/v1/freelance/bills/{id}/html'>open invoice</a>",
            id=obj.id)


def run_hook(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for hook in queryset.all():
        actions.sync_single_issue(json.loads(hook.payload))


run_hook.short_description = 'Process IssueHook'


def run_hook_delayed(modeladmin, request, queryset):
    # stay this here for use the poor mocking system
    for hook in queryset.all():
        async_repository_issue_github.delay(hook.id)


run_hook_delayed.short_description = 'Process IssueHook (delayed)'


@admin.register(RepositoryIssueWebhook)
class RepositoryIssueWebhookAdmin(admin.ModelAdmin):
    list_display = ('id', 'webhook_action', 'current_status', 'run_at', 'academy_slug', 'created_at')
    list_filter = ['status', 'webhook_action', 'academy_slug']
    actions = [run_hook, run_hook_delayed]

    def current_status(self, obj):
        colors = {
            'DONE': 'bg-success',
            'ERROR': 'bg-error',
            'PENDING': 'bg-warning',
        }
        return format_html(f"<span class='badge {colors[obj.status]}'>{obj.status}</span>")

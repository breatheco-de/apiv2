from django.contrib import admin, messages
from .models import Freelancer, Issue, Bill
from django.utils.html import format_html
from . import actions
# Register your models here.


def sync_issues(modeladmin, request, queryset):
    freelancers = queryset.all()
    for freelancer in freelancers:
        try:
            actions.sync_user_issues(freelancer)
        except ValueError as err:
            messages.error(request, err)


sync_issues.short_description = "Sync open issues"


def generate_bill(modeladmin, request, queryset):
    freelancers = queryset.all()
    for freelancer in freelancers:
        try:
            print(f"Genereting bill for {freelancer.user.email}")
            actions.generate_freelancer_bill(freelancer)
        except ValueError as err:
            messages.error(request, err)


generate_bill.short_description = "Generate bill"


def mark_as(queryset, status, request):
    freelancers = {}
    issues = queryset.all()

    try:
        for i in issues:
            if i.bill is not None and i.bill.status != 'DUE':
                raise Exception(
                    f"Github {i.github_number} cannot be updated because it was already approved for payment"
                )
            freelancers[i.freelancer.id] = i.freelancer
            i.status = status
            i.save()

        for freelancer_id in freelancers:
            actions.generate_freelancer_bill(freelancers[freelancer_id])
    except Exception as e:
        messages.error(request, e)


def mask_as_done(modeladmin, request, queryset):
    mark_as(queryset, 'DONE', request)


mask_as_done.short_description = "Mark as DONE"


def mask_as_todo(modeladmin, request, queryset):
    mark_as(queryset, 'TODO', request)


mask_as_todo.short_description = "Mark as TODO"


def mask_as_ignored(modeladmin, request, queryset):
    mark_as(queryset, 'IGNORED', request)


mask_as_ignored.short_description = "Mark as IGNORED"


@admin.register(Freelancer)
class FreelancerAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'full_name', "email"]
    raw_id_fields = ["user", "github_user"]
    actions = [sync_issues, generate_bill]

    def full_name(self, obj):
        return obj.user.first_name + " " + obj.user.last_name

    def email(self, obj):
        return obj.user.email


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    search_fields = [
        'title', 'freelancer__user__email', 'freelancer__user__first_name',
        'freelancer__user__last_name'
    ]
    list_display = ('id', 'github_number', 'freelancer', 'title', 'status',
                    'duration_in_hours', 'bill_id', 'github_url')
    list_filter = ['status', 'bill__status']
    actions = [mask_as_todo, mask_as_done, mask_as_ignored]

    def github_url(self, obj):
        return format_html(
            "<a rel='noopener noreferrer' target='_blank' href='{url}'>open in github</a>",
            url=obj.url)


def mask_as_paid(modeladmin, request, queryset):
    issues = queryset.update(status='PAID')


mask_as_paid.short_description = "Mark as PAID"


def mask_as_approved(modeladmin, request, queryset):
    issues = queryset.update(status='APPROVED')


mask_as_approved.short_description = "Mark as APPROVED"


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('id', 'freelancer', 'status', 'total_duration_in_hours',
                    'total_price', 'paid_at', 'invoice_url')
    list_filter = ['status']
    actions = [mask_as_paid, mask_as_approved]

    def invoice_url(self, obj):
        return format_html(
            "<a rel='noopener noreferrer' target='_blank' href='/v1/freelance/bills/{id}/html'>open invoice</a>",
            id=obj.id)

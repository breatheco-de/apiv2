from django.contrib import admin, messages
from .models import Freelancer, Issue, Bill, AcademyFreelanceProject, FreelanceProjectMember, ProjectInvoice
from django.utils.html import format_html
from . import actions
from breathecode.utils.admin import change_field

# Register your models here.


@admin.display(description="Sync open issues")
def sync_issues(modeladmin, request, queryset):
    freelancers = queryset.all()
    for freelancer in freelancers:
        try:
            count = actions.sync_user_issues(freelancer)
            messages.success(message=f"{count} issues successfully synched!", request=request)
        except ValueError as err:
            messages.error(request, err)


def generate_freelancer_bill(modeladmin, request, queryset):
    freelancers = queryset.all()
    for freelancer in freelancers:
        try:
            actions.generate_freelancer_bill(freelancer)
            messages.success(message="Success!", request=request)
        except ValueError as err:
            messages.error(request, err)


def mark_as(queryset, status, request):
    freelancers = {}
    issues = queryset.all()

    try:
        for i in issues:
            if i.bill is not None and i.bill.status != "DUE":
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


@admin.register(Freelancer)
class FreelancerAdmin(admin.ModelAdmin):
    list_display = ["user_id", "full_name", "email", "github", "price_per_hour"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    raw_id_fields = ["user", "github_user"]
    actions = [sync_issues, generate_freelancer_bill]

    def full_name(self, obj):
        return obj.user.first_name + " " + obj.user.last_name

    def email(self, obj):
        return obj.user.email

    def github(self, obj):
        if obj.github_user is None:
            return format_html("<span class='badge bg-error'> Missing github connection</span>")

        if obj.price_per_hour == 0 or obj.price_per_hour is None:
            return format_html("<span class='badge bg-error'> Missing rate per hour</span>")

        return format_html("<span class='badge bg-success'>Connected to Github</span>")


def resync_single_issue(modeladmin, request, queryset):
    issues = queryset.all()
    for i in issues:
        try:
            actions.sync_single_issue(i)
            messages.success(message="Success!", request=request)
        except ValueError as err:
            messages.error(request, err)


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    search_fields = [
        "title",
        "freelancer__user__email",
        "freelancer__user__first_name",
        "freelancer__user__last_name",
        "github_number",
    ]
    list_display = (
        "id",
        "github_number",
        "freelancer",
        "title",
        "status",
        "duration_in_hours",
        "bill_id",
        "github_url",
    )
    list_filter = ["status", "bill__status"]
    actions = [resync_single_issue] + change_field(["TODO", "DONE", "IGNORED", "DRAFT", "DOING"], name="status")

    def github_url(self, obj):
        return format_html("<a rel='noopener noreferrer' target='_blank' href='{url}'>open in github</a>", url=obj.url)


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("id", "freelancer", "status", "total_duration_in_hours", "total_price", "paid_at", "invoice_url")
    list_filter = ["status"]
    actions = change_field(["PAID", "APPROVED", "IGNORED", "DUE"], name="status")

    def invoice_url(self, obj):
        return format_html(
            "<a rel='noopener noreferrer' target='_blank' href='/v1/freelance/bills/{id}/html'>open invoice</a>",
            id=obj.id,
        )


def generate_project_invoice(modeladmin, request, queryset):
    projects = queryset.all()
    for p in projects:
        try:
            actions.generate_project_invoice(p)
        except ValueError as err:
            raise err
            messages.error(request, err)


@admin.register(AcademyFreelanceProject)
class AcademyFreelanceProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "academy", "total_client_hourly_price")
    list_filter = ["academy"]
    actions = [generate_project_invoice]


@admin.register(FreelanceProjectMember)
class FreelanceProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("freelancer", "project", "total_cost_hourly_price", "total_client_hourly_price")
    list_filter = ["project"]
    search_fields = [
        "project__title",
        "freelancer__user__email",
        "freelancer__user__first_name",
        "freelancer__user__last_name",
    ]


@admin.register(ProjectInvoice)
class ProjectInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "status", "total_duration_in_hours", "total_price", "paid_at")
    list_filter = ["status"]
    actions = change_field(["PAID", "APPROVED", "IGNORED", "DUE"], name="status")

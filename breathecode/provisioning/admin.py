import logging
from django.contrib import admin
from django.utils.html import format_html
from breathecode.utils.admin import change_field
from breathecode.provisioning import tasks
from .models import (
    ProvisioningConsumptionEvent,
    ProvisioningConsumptionKind,
    ProvisioningPrice,
    ProvisioningUserConsumption,
    ProvisioningVendor,
    ProvisioningMachineTypes,
    ProvisioningAcademy,
    ProvisioningBill,
    ProvisioningContainer,
    ProvisioningProfile,
)

logger = logging.getLogger(__name__)


@admin.register(ProvisioningVendor)
class ProvisioningVendorAdmin(admin.ModelAdmin):
    # form = CustomForm
    search_fields = ["name"]
    list_display = ("id", "name")


@admin.register(ProvisioningMachineTypes)
class ProvisioningMachineTypesAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "vendor"]
    search_fields = ("name", "slug")
    list_filter = ["vendor"]


@admin.register(ProvisioningAcademy)
class ProvisioningAcademyAdmin(admin.ModelAdmin):
    list_display = ["academy", "vendor", "created_at"]
    search_fields = ("academy__name", "academy__slug")
    list_filter = ["vendor"]


@admin.register(ProvisioningConsumptionKind)
class ProvisioningConsumptionKindAdmin(admin.ModelAdmin):
    list_display = ("id", "product_name", "sku")
    search_fields = ["product_name"]
    list_filter = ["product_name"]
    actions = []


@admin.register(ProvisioningPrice)
class ProvisioningPriceAdmin(admin.ModelAdmin):
    list_display = ("id", "currency", "unit_type", "price_per_unit", "multiplier")
    search_fields = ["currency__code"]
    list_filter = ["currency__code", "unit_type"]
    actions = []


@admin.register(ProvisioningConsumptionEvent)
class ProvisioningConsumptionEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "registered_at",
        "external_pk",
        "csv_row",
        "vendor",
        "quantity",
        "repository_url",
        "task_associated_slug",
    )
    search_fields = ["repository_url", "task_associated_slug", "provisioninguserconsumption__bills__hash"]
    list_filter = ["vendor"]
    actions = []


@admin.register(ProvisioningUserConsumption)
class ProvisioningUserConsumptionAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "kind", "amount", "quantity", "_status", "processed_at")
    search_fields = ["username", "events__task_associated_slug", "bills__hash"]
    list_filter = ["bills__academy", "status"]
    actions = []

    def _status(self, obj):
        colors = {
            "PERSISTED": "bg-success",
            "PENDING": "bg-error",
            "ERROR": "bg-error",
            "IGNORED": "bg-warning",
            None: "bg-warning",
        }

        def from_status(s):
            if s in colors:
                return colors[s]
            return ""

        return format_html(f"<p class='{from_status(obj.status)}'>{obj.status}</p><small>{obj.status_text}</small>")


def force_calculate_bill(modeladmin, request, queryset):
    for x in queryset.all():
        tasks.calculate_bill_amounts.delay(x.hash, force=True)


def reverse_bill(modeladmin, request, queryset):
    for x in queryset.all():
        tasks.reverse_upload(x.hash)


@admin.register(ProvisioningBill)
class ProvisioningBillAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "vendor",
        "academy",
        "_status",
        "total_amount",
        "currency_code",
        "paid_at",
        "invoice_url",
    )
    search_fields = ["academy__name", "academy__slug", "id", "title"]
    list_filter = ["academy", "status", "vendor"]

    actions = [force_calculate_bill, reverse_bill] + change_field(["DUE", "DISPUTED", "PAID", "PENDING"], name="status")

    def invoice_url(self, obj):
        return format_html(
            "<a rel='noopener noreferrer' target='_blank' href='/v1/provisioning/bill/{id}/html'>open invoice</a>",
            id=obj.id,
        )

    def _status(self, obj):
        colors = {
            "PAID": "bg-success",
            "DISPUTED": "bg-error",
            "DUE": "bg-warning",
            None: "bg-warning",
            "IGNORED": "",
        }

        def from_status(s):
            if s in colors:
                return colors[s]
            return ""

        return format_html(f"<p class='{from_status(obj.status)}'>{obj.status}</p><small>{obj.status_details}</small>")


@admin.register(ProvisioningContainer)
class ProvisioningContainerAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "display_name", "last_used_at")
    search_fields = ["display_name", "user__firstname", "user__lastname", "user__email", "task_associated_slug"]
    list_filter = ["status"]
    actions = []


@admin.register(ProvisioningProfile)
class ProvisioningProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "academy", "vendor", "cohorts_list", "member_list")
    search_fields = [
        "academy__name",
        "academy__slug",
    ]
    raw_id_fields = ["members", "cohorts"]
    list_filter = ["vendor"]
    actions = []

    def cohorts_list(self, obj):
        return format_html(", ".join([str(c) for c in obj.cohorts.all()]))

    def member_list(self, obj):
        return format_html(", ".join([str(pa) for pa in obj.members.all()]))

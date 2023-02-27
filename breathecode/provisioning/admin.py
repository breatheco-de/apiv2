import logging, secrets
from django.contrib import admin, messages
from django import forms
from .models import (ProvisioningVendor, ProvisioningMachineTypes, ProvisioningAcademy, ProvisioningBill,
                     ProvisioningActivity, Container)
# from .actions import ()
from django.utils import timezone
from breathecode.utils.validation_exception import ValidationException

logger = logging.getLogger(__name__)


@admin.register(ProvisioningVendor)
class ProvisioningVendorAdmin(admin.ModelAdmin):
    form = CustomForm
    search_fields = ['name']
    list_display = ('id', 'name')


@admin.register(ProvisioningMachineTypes)
class ProvisioningMachineTypesAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'vendor']
    search_fields = ('name', 'slug')
    list_filter = ['vendor']


@admin.register(ProvisioningAcademy)
class ProvisioningAcademyAdmin(admin.ModelAdmin):
    list_display = ['academy', 'vendor', 'created_at']
    search_fields = ('academy__name', 'academy__slug')
    list_filter = ['vendor']


@admin.register(ProvisioningActivity)
class ProvisioningActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'username', 'registered_at', 'product_name', 'sku', 'quantity')
    search_fields = ['username', 'task_associated_slug']
    list_filter = ['bill__academy', 'status']
    actions = []

    def _status(self, obj):
        colors = {
            'PERSISTED': 'bg-success',
            'PENDING': 'bg-error',
            'ERROR': 'bg-error',
            None: 'bg-warning',
        }

        def from_status(s):
            if s in colors:
                return colors[s]
            return ''

        return format_html(
            f"<p class='{from_status(obj.status)}'>{obj.status}</p><small>{obj.storage_status_text}</small>")


@admin.register(ProvisioningBill)
class ProvisioningBillAdmin(admin.ModelAdmin):
    list_display = ('id', 'academy', '_status', 'total_amount', 'currency_code', 'paid_at')
    search_fields = ['academy__name', 'academy__slug', 'id']
    list_filter = ['academy', 'status']
    actions = []

    def _status(self, obj):
        colors = {
            'PAID': 'bg-success',
            'DISPUTED': 'bg-error',
            'DUE': 'bg-warning',
            None: 'bg-warning',
            'IGNORED': '',
        }

        def from_status(s):
            if s in colors:
                return colors[s]
            return ''

        return format_html(
            f"<p class='{from_status(obj.storage_status)}'>{obj.storage_status}</p><small>{obj.storage_status_text}</small>"
        )


@admin.register(ProvisioningContainer)
class ProvisioningContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'display_name', 'last_used_at')
    search_fields = [
        'display_name', 'user__firstname', 'user__lastname', 'user__email', 'task_associated_slug'
    ]
    list_filter = ['status']
    actions = []

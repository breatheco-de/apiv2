import logging
from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort
from breathecode.authenticate.models import ProfileAcademy
from django.utils import timezone

logger = logging.getLogger(__name__)


class ProvisioningVendor(models.Model):
    name = models.CharField(max_length=200)
    api_url = models.URLField(blank=True)

    workspaces_url = models.URLField(help_text='Points to the place were you can see all your containers')
    invite_url = models.URLField(
        help_text='Some vendors (like Gitpod) allow to share invite link to automatically join')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name


class ProvisioningProfile(models.Model):
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    vendor = models.ForeignKey(ProvisioningVendor, on_delete=models.SET_NULL, null=True, default=None)

    cohorts = models.ManyToManyField(
        Cohort,
        blank=True,
        help_text='If set, only these cohorts will be provisioned with this vendor in this academy')
    members = models.ManyToManyField(
        ProfileAcademy,
        blank=True,
        help_text='If set, only these members will be provisioned with this vendor in this academy')


class ProvisioningMachineTypes(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80)
    description = models.CharField(max_length=255)
    vendor = models.ForeignKey(ProvisioningVendor, on_delete=models.SET_NULL, null=True, default=None)

    cpu_cores = models.IntegerField()
    ram_in_bytes = models.IntegerField()
    disk_in_bytes = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name


class ProvisioningAcademy(models.Model):
    vendor = models.ForeignKey(ProvisioningVendor, on_delete=models.SET_NULL, null=True, default=None)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    credentials_key = models.CharField(max_length=200, blank=True)
    credentials_token = models.CharField(max_length=200, blank=True)

    container_idle_timeout = models.IntegerField(
        default=15, help_text='If the container is idle for X amount of minutes, it will be shut down')
    max_active_containers = models.IntegerField(
        default=2, help_text='If you already have X active containers you wont be able to create new ones. ')
    allowed_machine_types = models.ManyToManyField(ProvisioningMachineTypes, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.academy) + ' on ' + str(self.vendor)


DUE = 'DUE'
DISPUTED = 'DISPUTED'
PAID = 'PAID'
IGNORED = 'IGNORED'
BILL_STATUS = (
    (DUE, 'Due'),
    (DISPUTED, 'Disputed'),
    (IGNORED, 'Ignored'),
    (PAID, 'Paid'),
)


class ProvisioningBill(models.Model):
    total_amount = models.FloatField()
    currency_code = models.CharField(max_length=3, default='usd')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=BILL_STATUS, default=DUE)
    paid_at = models.DateTimeField(null=True, default=None, blank=True)
    status_details = models.TextField(default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.id) + ' ' + str(self.academy) + ' - ' + str(self.total_amount) + str(
            self.currency_code)


PENDING = 'PENDING'
PERSISTED = 'PERSISTED'
ERROR = 'ERROR'
ACTIVITY_STATUS = (
    (PENDING, 'Pending'),
    (PERSISTED, 'Persisted'),
    (ERROR, 'Error'),
)


class ProvisioningActivity(models.Model):
    username = models.CharField(
        max_length=80, help_text='Native username in the provisioning platform, E.g: github username')
    registered_at = models.DateTimeField(
        null=True,
        default=None,
        blank=True,
        help_text='When the activitiy happened, this field comes form the provisioning vendor')
    product_name = models.CharField(max_length=100)
    sku = models.CharField(max_length=100)

    quantity = models.FloatField()
    unit_type = models.CharField(max_length=100)

    price_per_unit = models.FloatField(help_text='Price paid to the provisioning vendor, E.g: Github')
    currency_code = models.CharField(max_length=3)
    multiplier = models.FloatField(blank=True,
                                   null=True,
                                   help_text='To increase price in a certain percentage')
    repository_url = models.URLField()
    task_associated_slug = models.SlugField(
        max_length=100, help_text='What assignment was the the student trying to complete with this')
    bill = models.ForeignKey(ProvisioningBill, blank=True, null=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=ACTIVITY_STATUS, default=PENDING)
    status_text = models.CharField(max_length=255)
    processed_at = models.DateTimeField(null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class ProvisioningContainer(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    web_url = models.URLField()
    status = models.CharField(max_length=50, help_text='We have no control over this. Reported by the vendor')
    display_name = models.CharField(max_length=50)
    last_used_at = models.DateTimeField(null=True, default=None, blank=True)
    provisioned_at = models.DateTimeField(null=True, default=None, blank=True)

    has_unpushed_changes = models.BooleanField(default=False)
    has_uncommitted_changes = models.BooleanField(default=False)
    branch_name = models.CharField(max_length=100, null=True, blank=True, default=None)

    task_associated_slug = models.SlugField(
        max_length=100, help_text='What assignment was the the student trying to complete with this')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

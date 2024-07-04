import logging

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from breathecode.admissions.models import Academy, Cohort
from breathecode.authenticate.models import ProfileAcademy
from breathecode.payments.models import Currency

logger = logging.getLogger(__name__)


class ProvisioningVendor(models.Model):
    name = models.CharField(max_length=200)
    api_url = models.URLField(blank=True)

    workspaces_url = models.URLField(help_text="Points to the place were you can see all your containers")
    invite_url = models.URLField(
        blank=True,
        null=True,
        default=None,
        help_text="Some vendors (like Gitpod) allow to share invite link to automatically join",
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name


class ProvisioningProfile(models.Model):
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    vendor = models.ForeignKey(ProvisioningVendor, on_delete=models.SET_NULL, null=True, default=None)

    cohorts = models.ManyToManyField(
        Cohort, blank=True, help_text="If set, only these cohorts will be provisioned with this vendor in this academy"
    )
    members = models.ManyToManyField(
        ProfileAcademy,
        blank=True,
        help_text="If set, only these members will be provisioned with this vendor in this academy",
    )

    def __str__(self):
        return self.academy.name + " on " + self.vendor.name


# FIXME: the model name is wrong, it should be ProvisioningMachineType
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
        default=15, help_text="If the container is idle for X amount of minutes, it will be shut down"
    )
    max_active_containers = models.IntegerField(
        default=2, help_text="If you already have X active containers you wont be able to create new ones. "
    )
    allowed_machine_types = models.ManyToManyField(ProvisioningMachineTypes, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.academy) + " on " + str(self.vendor)


DUE = "DUE"
DISPUTED = "DISPUTED"
PAID = "PAID"
IGNORED = "IGNORED"
PENDING = "PENDING"
ERROR = "ERROR"
BILL_STATUS = (
    (DUE, "Due"),
    (DISPUTED, "Disputed"),
    (IGNORED, "Ignored"),
    (PENDING, "Pending"),
    (PAID, "Paid"),
    (ERROR, "Error"),
)


class ProvisioningBill(models.Model):
    vendor = models.ForeignKey(ProvisioningVendor, on_delete=models.SET_NULL, null=True, default=None, blank=True)
    total_amount = models.FloatField(default=0)
    fee = models.FloatField(default=0)
    hash = models.CharField(max_length=64, blank=True, null=True, default=None, db_index=True)
    currency_code = models.CharField(max_length=3, default="USD")
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, db_index=True)
    status = models.CharField(max_length=20, choices=BILL_STATUS, default=DUE, db_index=True)
    paid_at = models.DateTimeField(null=True, default=None, blank=True, db_index=True)
    archived_at = models.DateTimeField(null=True, default=None, blank=True)
    status_details = models.TextField(default=None, null=True, blank=True)
    stripe_id = models.CharField(max_length=32, null=True, default=None, blank=True, help_text="Stripe id")
    stripe_url = models.URLField(default=None, null=True, blank=True)
    started_at = models.DateTimeField(null=True, default=None, blank=True)
    ended_at = models.DateTimeField(null=True, default=None, blank=True)
    title = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        default=None,
        help_text="This title should describe what the Bill is about. I.e.: April's bill. (MAX 64 chars)",
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self):
        if self.status == PAID and self.paid_at is None:
            self.paid_at = timezone.now()

        self.currency_code = self.currency_code.upper()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.id) + " " + str(self.academy) + " - " + str(self.total_amount) + str(self.currency_code)


PENDING = "PENDING"
PERSISTED = "PERSISTED"
WARNING = "WARNING"
ACTIVITY_STATUS = (
    (PENDING, "Pending"),
    (PERSISTED, "Persisted"),
    (IGNORED, "Ignored"),
    (WARNING, "Warning"),
    (ERROR, "Error"),
)


class ProvisioningConsumptionKind(models.Model):
    product_name = models.CharField(max_length=100)
    sku = models.CharField(max_length=100)

    def __str__(self):
        return self.product_name + " - " + self.sku


class ProvisioningPrice(models.Model):
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    unit_type = models.CharField(max_length=100)
    price_per_unit = models.FloatField(help_text="Price paid to the provisioning vendor, E.g: Github")
    multiplier = models.FloatField(
        blank=True, null=False, default=1, help_text="To increase price in a certain percentage"
    )

    def __str__(self):
        return self.currency.code + " - " + self.unit_type + " - " + str(self.price_per_unit)

    def get_price(self, how_many):
        return self.price_per_unit * self.multiplier * how_many


class ProvisioningConsumptionEvent(models.Model):
    registered_at = models.DateTimeField(
        help_text="When the activity happened, this field comes form the provisioning vendor"
    )

    external_pk = models.CharField(max_length=100, blank=True, null=True, default=None)
    csv_row = models.IntegerField()
    vendor = models.ForeignKey(ProvisioningVendor, on_delete=models.CASCADE, null=True, blank=True, default=None)

    quantity = models.FloatField()
    price = models.ForeignKey(ProvisioningPrice, on_delete=models.CASCADE)

    repository_url = models.URLField(null=True, blank=False)
    task_associated_slug = models.SlugField(
        max_length=100,
        null=True,
        blank=False,
        help_text="What assignment was the the student trying to complete with this",
    )

    def __str__(self):
        return str(self.quantity) + " - " + self.task_associated_slug


class ProvisioningUserConsumption(models.Model):
    username = models.CharField(
        max_length=80, help_text="Native username in the provisioning platform, E.g: github username"
    )
    hash = models.CharField(max_length=64, blank=True, null=True, default=None)
    kind = models.ForeignKey(ProvisioningConsumptionKind, on_delete=models.CASCADE)

    bills = models.ManyToManyField(ProvisioningBill, blank=True)
    events = models.ManyToManyField(ProvisioningConsumptionEvent, blank=True, editable=False)
    amount = models.FloatField(default=0)
    quantity = models.FloatField(default=0)

    status = models.CharField(max_length=20, choices=ACTIVITY_STATUS, default=PENDING)
    status_text = models.CharField(max_length=255)
    processed_at = models.DateTimeField(null=True, default=None, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self) -> str:
        return str(self.username) + " - " + self.kind.product_name + " - " + str(self.kind.sku)


class ProvisioningContainer(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    web_url = models.URLField()
    status = models.CharField(max_length=50, help_text="We have no control over this. Reported by the vendor")
    display_name = models.CharField(max_length=50)
    last_used_at = models.DateTimeField(null=True, default=None, blank=True)
    provisioned_at = models.DateTimeField(null=True, default=None, blank=True)

    has_unpushed_changes = models.BooleanField(default=False)
    has_uncommitted_changes = models.BooleanField(default=False)
    branch_name = models.CharField(max_length=100, null=True, blank=True, default=None)

    task_associated_slug = models.SlugField(
        max_length=100, help_text="What assignment was the the student trying to complete with this"
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

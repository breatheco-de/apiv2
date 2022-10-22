import re
from django.contrib.auth.models import Group, User
from django.db import models

from breathecode.admissions.models import DRAFT, Academy, Cohort
from breathecode.mentorship.models import MentorshipService

# https://devdocs.prestashop-project.org/1.7/webservice/resources/warehouses/


class Currency(models.Model):
    code = models.CharField(max_length=3)
    name = models.CharField(max_length=20)

    # to represent the value
    template = models.CharField(max_length=15)

    # to extract the value
    regex = models.CharField(max_length=15)

    def format_value(self, value):
        return self.template.format(value)

    def get_value(self, value):
        # regex = re.compile(self.regex)
        raise NotImplementedError()


class Price(models.Model):
    price = models.FloatField(default=0)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)


class Asset(models.Model):
    slug = models.CharField(max_length=60, unique=True)
    title = models.CharField(max_length=60)
    description = models.CharField(max_length=255)
    prices = models.ManyToManyField(Price)

    owner = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    private = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class Service(Asset):

    groups = models.ManyToManyField(Group)
    cohorts = models.ManyToManyField(Cohort)
    mentorship_services = models.ManyToManyField(MentorshipService)

    def clean(self):
        if self.unit_type:
            self.unit_type = self.unit_type.upper()

    def __str__(self):
        return self.slug

    def save(self):
        self.full_clean()

        super().save()


UNIT = 'UNIT'
SERVICE_UNITS = [
    (UNIT, 'Unit'),
]


class CommonServiceItem:
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    # the unit between a service and a product are different
    unit_type = models.CharField(max_length=10, choices=SERVICE_UNITS, default=UNIT)
    how_many = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.service.slug} {self.how_many}'


# this class is used as referenced of units of a service can be used
class ServiceItem(models.Model, CommonServiceItem):
    pass


# this class can be consumed by the api
class ServiceCreditItem(models.Model, CommonServiceItem):
    pass


DAY = 'DAY'
WEEK = 'WEEK'
MONTH = 'MONTH'
YEAR = 'YEAR'
PAY_EVERY_UNIT = [
    (DAY, 'Day'),
    (WEEK, 'Week'),
    (MONTH, 'Month'),
    (YEAR, 'Year'),
]

DRAFT = 'DRAFT'
VISIBLE = 'VISIBLE'
HIDDEN = 'HIDDEN'
DELETED = 'DELETED'
PLAN_STATUS = [
    (DRAFT, 'Draft'),
    (VISIBLE, 'Visible'),
    (HIDDEN, 'Hidden'),
    (DELETED, 'Deleted'),
]


class Plan(models.Model):
    slug = models.CharField(max_length=60, unique=True)
    title = models.CharField(max_length=60)
    description = models.CharField(max_length=255)
    status = models.CharField(max_length=7, choices=PLAN_STATUS, default=DRAFT)
    prices = models.ManyToManyField(Price)

    renew_every = models.IntegerField(default=1)
    renew_every_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    trial_duration = models.IntegerField(default=1)
    trial_duration_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    services = models.ManyToManyField(ServiceItem)
    owner = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)


FREE_TRIAL = 'FREE_TRIAL'
ACTIVE = 'ACTIVE'
CANCELLED = 'CANCELLED'
DEPRECATED = 'DEPRECATED'
PAYMENT_ISSUE = 'PAYMENT_ISSUE'
SUBSCRIPTION_STATUS = [
    (FREE_TRIAL, 'Free trial'),
    (ACTIVE, 'Active'),
    (CANCELLED, 'Cancelled'),
    (DEPRECATED, 'Deprecated'),
    (PAYMENT_ISSUE, 'Payment issue'),
]


class Consumable(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    # the unit between a service and a product are different
    unit_type = models.CharField(max_length=10, choices=SERVICE_UNITS, default=UNIT)
    how_many = models.IntegerField(default=0)

    # if null, this is valid until resources are exhausted
    valid_until = models.DateTimeField(null=True, blank=True, default=None)


FULFILLED = 'FULFILLED'
REJECTED = 'REJECTED'
PENDING = 'PENDING'
INVOICE_STATUS = [
    (FULFILLED, 'Fulfilled'),
    (REJECTED, 'Rejected'),
    (PENDING, 'Pending'),
]


class Invoice(models.Model):
    amount = models.FloatField(default=0)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    paid_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=INVOICE_STATUS, default=PENDING)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


#TODO: think more about subscriptions
class Subscription(models.Model):
    paid_at = models.DateTimeField()
    status = models.CharField(max_length=9, choices=SUBSCRIPTION_STATUS, default=ACTIVE)

    is_cancellable = models.BooleanField(default=True)
    is_refundable = models.BooleanField(default=True)
    invoices = models.ManyToManyField(Invoice)

    # if null, this is valid until resources are exhausted
    valid_until = models.DateTimeField()
    last_renew = models.DateTimeField()
    renew_credits_at = models.DateTimeField()

    pay_every = models.IntegerField(default=1)
    pay_every_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    renew_every = models.IntegerField(default=1)
    renew_every_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    services = models.ManyToManyField(ServiceItem)
    plans = models.ManyToManyField(Plan)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class Credit(models.Model):
    # if null, this is valid until resources are exhausted
    valid_until = models.DateTimeField(null=True, blank=True, default=None)
    is_free_trial = models.BooleanField(default=False)

    services = models.ManyToManyField(ServiceCreditItem)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

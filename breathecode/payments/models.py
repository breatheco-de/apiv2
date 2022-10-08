from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy


class Asset(models.Model):
    slug = models.CharField(max_length=60, unique=True)
    title = models.CharField(max_length=60)
    description = models.CharField(max_length=255)
    price = models.FloatField(default=0)

    owner = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    private = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


COHORT = 'COHORT'
MENTORSHIP = 'MENTORSHIP'
SERVICE_TYPE = [
    (COHORT, 'Unit'),
    (MENTORSHIP, 'Mentorship'),
]


class Service(Asset):

    service_type = models.CharField(max_length=10, choices=SERVICE_TYPE, default=COHORT)

    def clean(self):
        if self.unit_type:
            self.unit_type = self.unit_type.upper()

    def __str__(self):
        return self.slug


class CohortService(Service):
    cohort = models.ForeignKey(Academy, on_delete=models.CASCADE)

    def clean(self):
        super().clean()

        self.service_type = COHORT

    def save(self):
        self.full_clean()

        super().save()


UNIT = 'UNIT'
SERVICE_UNITS = [
    (UNIT, 'Unit'),
]


class ServiceInvoiceItem(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    # the unit between a service and a product are different
    unit_type = models.CharField(max_length=10, choices=SERVICE_UNITS, default=UNIT)
    how_many = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.service.slug} {self.how_many}'


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


class Plan(models.Model):
    slug = models.CharField(max_length=60, unique=True)
    title = models.CharField(max_length=60)
    description = models.CharField(max_length=255)

    pay_every = models.IntegerField(default=1)
    pay_every_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    services = models.ManyToManyField(ServiceInvoiceItem)


class Invoice(models.Model):
    amount = models.FloatField(default=0)
    paid_at = models.DateTimeField()

    # if null, this is valid until resources are exhausted
    valid_until = models.DateTimeField(null=True, blank=True, default=None)

    user = models.ForeignKey(User)
    services = models.ManyToManyField(ServiceInvoiceItem)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

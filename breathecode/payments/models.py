from __future__ import annotations

import ast
from datetime import timedelta
import os
from typing import Optional
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils import timezone
# from breathecode.payments.signals import consume_service

from breathecode.admissions.models import DRAFT, Academy, Cohort, Country
from breathecode.events.models import EventType
from breathecode.authenticate.actions import get_user_settings
from breathecode.mentorship.models import MentorshipService
from currencies import Currency as CurrencyFormatter
from django.core.exceptions import ValidationError
from django import forms
from django.core.handlers.wsgi import WSGIRequest

from breathecode.utils.validators.language import validate_language_code
from . import signals
from breathecode.utils.i18n import translation

# https://devdocs.prestashop-project.org/1.7/webservice/resources/warehouses/

# ⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇
# ↕ Remember do not save the card info in the backend ↕
# ⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆


class Currency(models.Model):
    """
    Represents a currency.
    """

    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=20, unique=True)
    decimals = models.IntegerField(default=0)

    countries = models.ManyToManyField(Country,
                                       blank=True,
                                       related_name='currencies',
                                       help_text='Countries that use this currency officially')

    def format_price(self, value):
        currency = CurrencyFormatter('USD')
        currency.get_money_currency()
        return currency.get_money_format(value)

    def clean(self) -> None:
        self.code = self.code.upper()
        return super().clean()

    def __str__(self) -> str:
        return f'{self.name} ({self.code})'


class AbstractPriceByUnit(models.Model):
    """
    This model is used to store the price of a Product or a Service.
    """

    price_per_unit = models.FloatField(default=0)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)

    def format_price(self):
        return self.currency.format_price(self.price)

    class Meta:
        abstract = True


class AbstractPriceByTime(models.Model):
    """
    This model is used to store the price of a Product or a Service.
    """

    price_per_month = models.FloatField(default=None, blank=True, null=True)
    price_per_quarter = models.FloatField(default=None, blank=True, null=True)
    price_per_half = models.FloatField(default=None, blank=True, null=True)
    price_per_year = models.FloatField(default=None, blank=True, null=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)

    def format_price(self):
        return self.currency.format_price(self.price)

    class Meta:
        abstract = True


class AbstractAmountByTime(models.Model):
    """
    This model is used to store the price of a Product or a Service.
    """

    amount_per_month = models.FloatField(default=0)
    amount_per_quarter = models.FloatField(default=0)
    amount_per_half = models.FloatField(default=0)
    amount_per_year = models.FloatField(default=0)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)

    def format_price(self):
        return self.currency.format_price(self.price)

    class Meta:
        abstract = True


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


class AbstractAsset(AbstractPriceByUnit):
    """
    This model represents a product or a service that can be sold.
    """

    slug = models.CharField(max_length=60, unique=True)

    owner = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    #TODO: visibility and the capacities of disable a asset
    private = models.BooleanField(default=True)

    trial_duration = models.IntegerField(default=1)
    trial_duration_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class Service(AbstractAsset):
    """
    Represents the service that can be purchased by the customer.
    """

    groups = models.ManyToManyField(Group, blank=True)

    def __str__(self):
        return self.slug

    def save(self):
        self.full_clean()

        super().save()


class ServiceTranslation(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    lang = models.CharField(max_length=5, validators=[validate_language_code])
    title = models.CharField(max_length=60)
    description = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f'{self.lang}: {self.title}'


UNIT = 'UNIT'
SERVICE_UNITS = [
    (UNIT, 'Unit'),
]


class AbstractServiceItem(models.Model):
    """
    Common fields for ServiceItem and Consumable.
    """

    # the unit between a service and a product are different
    unit_type = models.CharField(max_length=10, choices=SERVICE_UNITS, default=UNIT)
    how_many = models.IntegerField(default=-1)

    class Meta:
        abstract = True


# this class is used as referenced of units of a service can be used
class ServiceItem(AbstractServiceItem):
    """
    This model is used as referenced of units of a service can be used.
    """

    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    is_renewable = models.BooleanField(default=False)

    # the below fields are useless when is_renewable=False
    renew_at = models.IntegerField(default=1)
    renew_at_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    def clean(self):
        is_test_env = os.getenv('ENV') == 'test'
        inside_mixer = hasattr(self, '__mixer__')
        if self.id and (not inside_mixer or (inside_mixer and not is_test_env)):
            raise forms.ValidationError('You cannot update a service item')

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save()

    def delete(self):
        raise forms.ValidationError('You cannot delete a service item')

    def __str__(self) -> str:
        return f'{self.service.slug} ({self.how_many})'


class ServiceItemFeature(models.Model):
    """
    This model is used as referenced of units of a service can be used.
    """

    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE)
    lang = models.CharField(max_length=5, validators=[validate_language_code])
    description = models.CharField(max_length=255)
    one_line_desc = models.CharField(max_length=30)

    def __str__(self) -> str:
        return f'{self.lang} {self.service_item.service.slug} ({self.service_item.how_many})'


class FinancingOption(models.Model):
    """
    This model is used as referenced of units of a service can be used.
    """

    monthly_price = models.FloatField(default=1)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)

    how_many_months = models.IntegerField(default=1)

    def __str__(self) -> str:
        return f'{self.monthly_price} {self.currency.code} per {self.how_many_months} months'


DRAFT = 'DRAFT'
ACTIVE = 'ACTIVE'
UNLISTED = 'UNLISTED'
DELETED = 'DELETED'
DISCONTINUED = 'DISCONTINUED'
PLAN_STATUS = [
    (DRAFT, 'Draft'),
    (ACTIVE, 'Active'),
    (UNLISTED, 'Unlisted'),
    (DELETED, 'Deleted'),
    (DISCONTINUED, 'Discontinued'),
]


class Plan(AbstractPriceByTime):
    """
    A plan is a group of services that can be purchased by a user.
    """

    slug = models.CharField(max_length=60, unique=True)
    financing_options = models.ManyToManyField(FinancingOption,
                                               blank=True,
                                               help_text='If the plan is renew, it would be ignore')

    is_renewable = models.BooleanField(
        default=True,
        help_text='Is if true, it will create a reneweval subscription instead of a plan financing')

    status = models.CharField(max_length=12, choices=PLAN_STATUS, default=DRAFT)

    time_of_life = models.IntegerField(default=1, blank=True, null=True)
    time_of_life_unit = models.CharField(max_length=10,
                                         choices=PAY_EVERY_UNIT,
                                         blank=True,
                                         null=True,
                                         default=MONTH)

    trial_duration = models.IntegerField(default=1)
    trial_duration_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    service_items = models.ManyToManyField(ServiceItem,
                                           blank=True,
                                           through='PlanServiceItem',
                                           through_fields=('plan', 'service_item'))

    owner = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    is_onboarding = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.slug

    def clean(self) -> None:
        if self.is_renewable and (not self.time_of_life or not self.time_of_life_unit):
            raise forms.ValidationError(
                'If the plan is renewable, you must set time_of_life and time_of_life_unit')

        if not self.is_renewable and (self.time_of_life or self.time_of_life_unit):
            raise forms.ValidationError(
                'If the plan is not renewable, you must not set time_of_life and time_of_life_unit')

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()

        super().save(*args, **kwargs)


class PlanTranslation(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    lang = models.CharField(max_length=5, validators=[validate_language_code])
    title = models.CharField(max_length=60)
    description = models.CharField(max_length=255)

    def save(self):
        self.full_clean()

        super().save()

    def __str__(self) -> str:
        return f'{self.lang} {self.title}: ({self.plan.slug})'


class PlanOffer(models.Model):
    original_plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    from_syllabus = models.ManyToManyField('admissions.Syllabus')
    suggested_plans = models.ManyToManyField(Plan, related_name='+')


class PlanOfferTranslation(models.Model):
    offer = models.ForeignKey(PlanOffer, on_delete=models.CASCADE)
    lang = models.CharField(max_length=5, validators=[validate_language_code])
    title = models.CharField(max_length=60)
    description = models.CharField(max_length=255)
    short_description = models.CharField(max_length=255)


PENDING = 'PENDING'
DONE = 'DONE'
CANCELLED = 'CANCELLED'
CONSUMPTION_SESSION_STATUS = [
    (PENDING, 'Pending'),
    (DONE, 'Done'),
    (CANCELLED, 'Cancelled'),
]

RENEWAL = 'RENEWAL'
CHECKING = 'CHECKING'
PAID = 'PAID'
BAG_STATUS = [
    (RENEWAL, 'Renewal'),
    (CHECKING, 'Checking'),
    (PAID, 'Paid'),
]

BAG = 'BAG'
CHARGE = 'CHARGE'
PREVIEW = 'PREVIEW'
BAG_TYPE = [
    (BAG, 'Bag'),
    (CHARGE, 'Charge'),
    (PREVIEW, 'Preview'),
]

NO_SET = 'NO_SET'
QUARTER = 'QUARTER'
HALF = 'HALF'
YEAR = 'YEAR'
CHOSEN_PERIOD = [
    (NO_SET, 'No set'),
    (MONTH, 'Month'),
    (QUARTER, 'Quarter'),
    (HALF, 'Half'),
    (YEAR, 'Year'),
]


class Bag(AbstractAmountByTime):
    """
    Represents a credit that can be used by a user to use a service.
    """

    status = models.CharField(max_length=8, choices=BAG_STATUS, default=CHECKING)
    type = models.CharField(max_length=7, choices=BAG_TYPE, default=BAG)
    chosen_period = models.CharField(max_length=7, choices=CHOSEN_PERIOD, default=NO_SET)
    how_many_installments = models.IntegerField(default=0)

    academy = models.ForeignKey('admissions.Academy', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service_items = models.ManyToManyField(ServiceItem, blank=True)
    plans = models.ManyToManyField(Plan, blank=True)
    selected_cohorts = models.ManyToManyField('admissions.Cohort', blank=True)

    is_recurrent = models.BooleanField(default=False)
    was_delivered = models.BooleanField(default=False)

    token = models.CharField(max_length=40, db_index=True, default=None, null=True, blank=True)
    expires_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.type} {self.status} {self.chosen_period}'


FULFILLED = 'FULFILLED'
REJECTED = 'REJECTED'
PENDING = 'PENDING'
REFUNDED = 'REFUNDED'
DISPUTED_AS_FRAUD = 'DISPUTED_AS_FRAUD'
INVOICE_STATUS = [
    (FULFILLED, 'Fulfilled'),
    (REJECTED, 'Rejected'),
    (PENDING, 'Pending'),
    (REFUNDED, 'Refunded'),
    (DISPUTED_AS_FRAUD, 'Disputed as fraud'),
]


class Invoice(models.Model):
    """
    Represents a payment made by a user
    """

    amount = models.FloatField(
        default=0,
        help_text='If amount is 0, transaction will not be sent to stripe or any other payment processor.')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    paid_at = models.DateTimeField()
    refunded_at = models.DateTimeField(null=True, blank=True, default=None)
    status = models.CharField(max_length=17, choices=INVOICE_STATUS, default=PENDING)

    bag = models.ForeignKey('Bag', on_delete=models.CASCADE)

    # actually return 27 characters
    stripe_id = models.CharField(max_length=32, null=True, default=None, blank=True)

    # actually return 27 characters
    refund_stripe_id = models.CharField(max_length=32, null=True, default=None, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.user.email} {self.amount} ({self.currency.code})'


FREE_TRIAL = 'FREE_TRIAL'
ACTIVE = 'ACTIVE'
CANCELLED = 'CANCELLED'
DEPRECATED = 'DEPRECATED'
PAYMENT_ISSUE = 'PAYMENT_ISSUE'
ERROR = 'ERROR'
FULLY_PAID = 'FULLY_PAID'
SUBSCRIPTION_STATUS = [
    (FREE_TRIAL, 'Free trial'),
    (ACTIVE, 'Active'),
    (CANCELLED, 'Cancelled'),
    (DEPRECATED, 'Deprecated'),
    (PAYMENT_ISSUE, 'Payment issue'),
    (ERROR, 'Error'),
    (FULLY_PAID, 'Fully Paid'),
]


class AbstractIOweYou(models.Model):
    """
    Common fields for all I owe you.
    """

    status = models.CharField(max_length=13, choices=SUBSCRIPTION_STATUS, default=ACTIVE)
    status_message = models.CharField(max_length=250, null=True, blank=True, default=None)

    invoices = models.ManyToManyField(Invoice, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    # Add this three foreign keys, but we have to make sure this 3 items match exactly with the possible
    # cohorts, service sets and eventtype sets that the PlanServiceItem is allowing.
    #
    # cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
    # mentorshipservice_set = models.ForeignKey(MentorshipServiceSet, on_delete=models.CASCADE)
    # eventtype_set = models.ForeignKey(EventTypeSet, on_delete=models.CASCADE)

    # this reminds the plans to change the stock scheduler on change
    plans = models.ManyToManyField(Plan, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class Subscription(AbstractIOweYou):
    """
    Allows to create a subscription to a plan and services.
    """

    # last time the subscription was paid
    paid_at = models.DateTimeField()

    is_refundable = models.BooleanField(default=True)

    # in this day the subscription needs being paid again
    next_payment_at = models.DateTimeField()

    # in this moment the subscription will be expired
    valid_until = models.DateTimeField(default=None, null=True, blank=True)

    # this reminds the service items to change the stock scheduler on change
    # only for consuming single items without having a plan, when you buy consumable quantities
    service_items = models.ManyToManyField(ServiceItem,
                                           blank=True,
                                           through='SubscriptionServiceItem',
                                           through_fields=('subscription', 'service_item'))

    # remember the chosen period to pay again
    pay_every = models.IntegerField(default=1)
    pay_every_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    def __str__(self) -> str:
        return f'{self.user.email} ({self.valid_until})'


class MentorshipServiceSet(models.Model):
    """
    M2M between plan and ServiceItem
    """

    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    mentorship_services = models.ManyToManyField(MentorshipService, blank=True)


class SubscriptionServiceItem(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE)

    cohorts = models.ManyToManyField(Cohort, blank=True)
    mentorship_service_set = models.ForeignKey(MentorshipServiceSet,
                                               on_delete=models.CASCADE,
                                               blank=True,
                                               null=True)

    def clean(self):
        if self.id and self.mentorship_service_set and self.cohorts.count():
            raise forms.ValidationError(
                translation(
                    self._lang,
                    en='You can not set cohorts and mentorship service set at the same time',
                    es='No puedes establecer cohortes y conjunto de servicios de mentoría al mismo tiempo'))

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.service_item)


class PlanFinancing(AbstractIOweYou):
    """
    Allows to financing a plan
    """

    # in this day the financing needs being paid again
    next_payment_at = models.DateTimeField()

    # in this moment the subscription will be expired
    valid_until = models.DateTimeField()

    # in this moment the subscription will be expired
    plan_expires_at = models.DateTimeField(default=None, null=True, blank=False)

    # this remember the current price per month
    monthly_price = models.FloatField(default=0)

    def __str__(self) -> str:
        return f'{self.user.email} ({self.valid_until})'

    def clean(self) -> None:
        settings = get_user_settings(self.user.id)

        if not self.monthly_price:
            raise forms.ValidationError(
                translation(settings.lang, en='Monthly price is required', es='Precio mensual es requerido'))

        if not self.plan_expires_at:
            raise forms.ValidationError(
                translation(settings.lang,
                            en='Plan expires at is required',
                            es='Plan expires at es requerido'))

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        return super().save(*args, **kwargs)


class Consumable(AbstractServiceItem):
    """
    This model is used to represent the units of a service that can be consumed.
    """

    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE)

    # if null, this is valid until resources are exhausted
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # this could be used for the queries on the consumer, to recognize which resource is belong the consumable
    cohort = models.ForeignKey(Cohort, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    event_type = models.ForeignKey(EventType, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    mentorship_service = models.ForeignKey(MentorshipService,
                                           on_delete=models.CASCADE,
                                           default=None,
                                           blank=True,
                                           null=True)

    # if null, this is valid until resources are exhausted
    valid_until = models.DateTimeField(null=True, blank=True, default=None)

    def clean(self) -> None:
        resources = [self.event_type, self.mentorship_service, self.cohort]

        how_many_resources_are_set = len([
            r for r in resources
            if ((not hasattr(r, 'exists') and r is not None) or (r and hasattr(r, 'exists') and r.exists()))
        ])

        settings = get_user_settings(self.user.id)

        if how_many_resources_are_set > 1:
            raise forms.ValidationError(
                translation(settings.lang,
                            en='A consumable can only be associated with one resource',
                            es='Un consumible solo se puede asociar con un recurso'))

        if not self.service_item:
            raise forms.ValidationError(
                translation(settings.lang,
                            en='A consumable must be associated with a service item',
                            es='Un consumible debe estar asociado con un artículo de un servicio'))

        return super().clean()

    def save(self):
        self.full_clean()

        super().save()

    def __str__(self):
        return f'{self.user.email}: {self.service_item.service.slug} ({self.how_many})'


class ConsumptionSession(models.Model):
    consumable = models.ForeignKey(Consumable, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    eta = models.DateTimeField()
    duration = models.DurationField(blank=False, default=timedelta)
    how_many = models.FloatField(default=0)
    status = models.CharField(max_length=12, choices=CONSUMPTION_SESSION_STATUS, default=PENDING)
    was_discounted = models.BooleanField(default=False)

    request = models.JSONField(default=dict, blank=True)

    # this should be used to get
    path = models.CharField(max_length=200, blank=True)
    related_id = models.IntegerField(default=None, blank=True, null=True)
    related_slug = models.CharField(max_length=200, default=None, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    @classmethod
    def build_session(
        cls,
        request: WSGIRequest,
        consumable: Consumable,
        delta: timedelta,
        # info: Optional[str] = None,
    ) -> 'ConsumptionSession':
        assert request, 'You must provide a request'
        assert consumable, 'You must provide a consumable'
        assert delta, 'You must provide a delta'

        utc_now = timezone.now()

        resource = consumable.cohort or consumable.mentorship_service or consumable.event_type
        id = resource.id if resource else 0
        slug = resource.slug if resource else ''

        path = resource.__class__._meta.app_label + '.' + resource.__class__.__name__ if resource else ''

        data = {
            'args': request.parser_context['args'],
            'kwargs': request.parser_context['kwargs'],
            'headers': {
                'academy': request.META.get('HTTP_ACADEMY')
            },
            'user': request.user.id,
        }

        # assert path, 'You must provide a path'
        assert delta, 'You must provide a delta'

        return cls.objects.create(
            request=data,
            consumable=consumable,
            eta=utc_now + delta,
            path=path,
            duration=delta,
            related_id=id,
            related_slug=slug,
            #   related_info=info,
            user=request.user)

    @classmethod
    def get_session(cls, request: WSGIRequest) -> 'ConsumptionSession':
        if not request.user.id:
            return None

        utc_now = timezone.now()
        data = {
            'args': request.parser_context['args'],
            'kwargs': request.parser_context['kwargs'],
            'headers': {
                'academy': request.META.get('HTTP_ACADEMY')
            },
            'user': request.user.id,
        }
        return cls.objects.filter(eta__gte=utc_now, request=data, user=request.user).first()

    def will_consume(self, how_many: float = 1.0) -> None:
        # avoid dependency circle
        from breathecode.payments.tasks import end_the_consumption_session

        self.how_many = how_many
        self.save()

        end_the_consumption_session.apply_async(args=(self.id, how_many), eta=self.eta)


class PlanServiceItem(models.Model):
    """
    M2M between plan and ServiceItem
    """

    _lang = 'en'

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE)

    # patterns
    cohort_pattern = models.CharField(max_length=80, default=None, blank=True, null=True)

    # available cohorts to be sold in this service and plan
    cohorts = models.ManyToManyField(Cohort, blank=True)

    # available mentorships service to be sold in this service and plan
    mentorship_service_set = models.ForeignKey(MentorshipServiceSet,
                                               on_delete=models.CASCADE,
                                               blank=True,
                                               null=True)

    def clean(self):
        if self.id and self.mentorship_service_set and self.cohorts.count():
            raise forms.ValidationError(
                translation(
                    self._lang,
                    en='You can not set cohorts and mentorship service set at the same time',
                    es='No puedes establecer cohortes y conjunto de servicios de mentoría al mismo tiempo'))

        if self.mentorship_service_set and self.cohort_pattern:
            raise forms.ValidationError(
                translation(
                    self._lang,
                    en='You can not set cohorts pattern and mentorship service set at the same time',
                    es='No puedes establecer patrón de cohortes y conjunto de servicios de mentoría al '
                    'mismo tiempo'))

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.service_item)


class PlanServiceItemHandler(models.Model):
    """
    M2M between plan and ServiceItem
    """

    handler = models.ForeignKey(PlanServiceItem, on_delete=models.CASCADE)

    # resources associated to this service item, one is required
    subscription = models.ForeignKey(Subscription,
                                     on_delete=models.CASCADE,
                                     null=True,
                                     blank=True,
                                     default=None)
    plan_financing = models.ForeignKey(PlanFinancing,
                                       on_delete=models.CASCADE,
                                       null=True,
                                       blank=True,
                                       default=None)

    def clean(self) -> None:
        resources = [self.subscription, self.plan_financing]
        how_many_resources_are_set = len([r for r in resources if r is not None])

        if how_many_resources_are_set == 0:
            raise forms.ValidationError('A PlanServiceItem must be associated with one resource')

        if how_many_resources_are_set != 1:
            raise forms.ValidationError('A PlanServiceItem can only be associated with one resource')

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.subscription or self.plan_financing or 'Unset')


class ServiceStockScheduler(models.Model):
    """
    This model is used to represent the units of a service that can be consumed.
    """

    # all this section are M2M service items, in the first case we have a query with subscription and service
    # item for schedule the renovations
    subscription_handler = models.ForeignKey(SubscriptionServiceItem,
                                             on_delete=models.CASCADE,
                                             default=None,
                                             blank=True,
                                             null=True)
    plan_handler = models.ForeignKey(PlanServiceItemHandler,
                                     on_delete=models.CASCADE,
                                     default=None,
                                     blank=True,
                                     null=True)

    # this reminds which scheduler generated the consumable
    consumables = models.ManyToManyField(Consumable, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True, default=None)

    def clean(self) -> None:
        resources = [self.subscription_handler, self.plan_handler]
        how_many_resources_are_set = len([r for r in resources if r is not None])

        if how_many_resources_are_set == 0:
            raise forms.ValidationError('A ServiceStockScheduler must be associated with one resource')

        if how_many_resources_are_set != 1:
            raise forms.ValidationError('A ServiceStockScheduler can only be associated with one resource')

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.subscription_handler and self.subscription_handler.subscription:
            return f'{self.subscription_handler.subscription.user.email} - {self.subscription_handler.service_item}'

        if self.plan_handler and self.plan_handler.subscription:
            return f'{self.plan_handler.subscription.user.email} - {self.plan_handler.handler.service_item}'

        if self.plan_handler and self.plan_handler.plan_financing:
            return f'{self.plan_handler.plan_financing.user.email} - {self.plan_handler.handler.service_item}'

        return 'Unset'


GOOD = 'GOOD'
BAD = 'BAD'
FRAUD = 'FRAUD'
UNKNOWN = 'UNKNOWN'
REPUTATION_STATUS = [
    (GOOD, 'Good'),
    (BAD, 'BAD'),
    (FRAUD, 'Fraud'),
    (UNKNOWN, 'Unknown'),
]


class PaymentContact(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='payment_contact')
    stripe_id = models.CharField(max_length=20)  # actually return 18 characters

    def __str__(self) -> str:
        return f'{self.user.email} ({self.stripe_id})'


class FinancialReputation(models.Model):
    """
    The purpose of this model is to store the reputation of a user, if the user has a bad reputation, the
    user will not be able to buy services.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='reputation')

    in_4geeks = models.CharField(max_length=17, choices=INVOICE_STATUS, default=GOOD)
    in_stripe = models.CharField(max_length=17, choices=INVOICE_STATUS, default=GOOD)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def get_reputation(self):
        """
        Returns the worst reputation between the two.
        """

        if self.in_4geeks == FRAUD or self.in_stripe == FRAUD:
            return FRAUD

        if self.in_4geeks == BAD or self.in_stripe == BAD:
            return BAD

        if self.in_4geeks == GOOD or self.in_stripe == GOOD:
            return GOOD

        return UNKNOWN

    def __str__(self) -> str:
        return f'{self.user.email} -> {self.get_reputation()}'

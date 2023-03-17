from __future__ import annotations

from datetime import timedelta
import os
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils import timezone
from django.db.models import Q

from breathecode.admissions.models import DRAFT, Academy, Cohort, Country
from breathecode.events.models import EventType
from breathecode.authenticate.actions import get_user_settings
from breathecode.mentorship.models import MentorshipService
from currencies import Currency as CurrencyFormatter
from django import forms
from django.core.handlers.wsgi import WSGIRequest

from breathecode.utils.validators.language import validate_language_code
from breathecode.utils.i18n import translation

# https://devdocs.prestashop-project.org/1.7/webservice/resources/warehouses/

# ⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇
# ↕ Remember do not save the card info in the backend ↕
# ⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆


class Currency(models.Model):
    """
    Represents a currency.
    """

    code = models.CharField(max_length=3,
                            unique=True,
                            help_text='ISO 4217 currency code (e.g. USD, EUR, MXN)')
    name = models.CharField(max_length=20,
                            unique=True,
                            help_text='Currency name (e.g. US Dollar, Euro, Mexican Peso)')
    decimals = models.IntegerField(default=0,
                                   help_text='Number of decimals (e.g. 2 for USD and EUR, 0 for JPY)')

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

    price_per_unit = models.FloatField(default=0, help_text='Price per unit')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text='Currency')

    def format_price(self):
        return self.currency.format_price(self.price)

    class Meta:
        abstract = True


class AbstractPriceByTime(models.Model):
    """
    This model is used to store the price of a Product or a Service.
    """

    price_per_month = models.FloatField(default=None, blank=True, null=True, help_text='Price per month')
    price_per_quarter = models.FloatField(default=None, blank=True, null=True, help_text='Price per quarter')
    price_per_half = models.FloatField(default=None, blank=True, null=True, help_text='Price per half')
    price_per_year = models.FloatField(default=None, blank=True, null=True, help_text='Price per year')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text='Currency')

    def format_price(self):
        return self.currency.format_price(self.price)

    class Meta:
        abstract = True


class AbstractAmountByTime(models.Model):
    """
    This model is used to store the price of a Product or a Service.
    """

    amount_per_month = models.FloatField(default=0, help_text='Amount per month')
    amount_per_quarter = models.FloatField(default=0, help_text='Amount per quarter')
    amount_per_half = models.FloatField(default=0, help_text='Amount per half')
    amount_per_year = models.FloatField(default=0, help_text='Amount per year')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text='Currency')

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

    slug = models.CharField(
        max_length=60,
        unique=True,
        help_text='A human-readable identifier, it must be unique and it can only contain letters, '
        'numbers and hyphens')

    owner = models.ForeignKey(Academy,
                              on_delete=models.CASCADE,
                              blank=True,
                              null=True,
                              help_text='Academy owner')
    #TODO: visibility and the capacities of disable a asset
    private = models.BooleanField(default=True, help_text='If the asset is private or not')

    trial_duration = models.IntegerField(default=1, help_text='Trial duration (e.g. 1, 2, 3, ...)')
    trial_duration_unit = models.CharField(max_length=10,
                                           choices=PAY_EVERY_UNIT,
                                           default=MONTH,
                                           help_text='Trial duration unit (e.g. DAY, WEEK, MONTH or YEAR)')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


COHORT = 'COHORT'
MENTORSHIP_SERVICE_SET = 'MENTORSHIP_SERVICE_SET'
EVENT_TYPE_SET = 'EVENT_TYPE_SET'
SERVICE_TYPES = [
    (COHORT, 'Cohort'),
    (MENTORSHIP_SERVICE_SET, 'Mentorship service set'),
    (EVENT_TYPE_SET, 'Event type set'),
]


class Service(AbstractAsset):
    """
    Represents the service that can be purchased by the customer.
    """

    groups = models.ManyToManyField(Group,
                                    blank=True,
                                    help_text='Groups that can access the customer that bought this service')

    type = models.CharField(max_length=22, choices=SERVICE_TYPES, default=COHORT, help_text='Service type')

    def __str__(self):
        return self.slug

    def save(self):
        self.full_clean()

        super().save()


class ServiceTranslation(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, help_text='Service')
    lang = models.CharField(max_length=5,
                            validators=[validate_language_code],
                            help_text='ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US')
    title = models.CharField(max_length=60, help_text='Title of the service')
    description = models.CharField(max_length=255, help_text='Description of the service')

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
    unit_type = models.CharField(max_length=10,
                                 choices=SERVICE_UNITS,
                                 default=UNIT,
                                 help_text='Unit type (e.g. UNIT))')
    how_many = models.IntegerField(default=-1, help_text='How many units of this service can be used')

    class Meta:
        abstract = True


# this class is used as referenced of units of a service can be used
class ServiceItem(AbstractServiceItem):
    """
    This model is used as referenced of units of a service can be used.
    """

    service = models.ForeignKey(Service, on_delete=models.CASCADE, help_text='Service')
    is_renewable = models.BooleanField(default=False, help_text='If the service is renewable or not')

    # the below fields are useless when is_renewable=False
    renew_at = models.IntegerField(
        default=1,
        help_text='Renew at (e.g. 1, 2, 3, ...) it going to be used to build the balance of '
        'customer')
    renew_at_unit = models.CharField(max_length=10,
                                     choices=PAY_EVERY_UNIT,
                                     default=MONTH,
                                     help_text='Renew at unit (e.g. DAY, WEEK, MONTH or YEAR)')

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

    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE, help_text='Service item')
    lang = models.CharField(max_length=5,
                            validators=[validate_language_code],
                            help_text='ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US')
    description = models.CharField(max_length=255, help_text='Description of the service item')
    one_line_desc = models.CharField(max_length=30, help_text='One line description of the service item')

    def __str__(self) -> str:
        return f'{self.lang} {self.service_item.service.slug} ({self.service_item.how_many})'


class FinancingOption(models.Model):
    """
    This model is used as referenced of units of a service can be used.
    """

    _lang = 'en'

    monthly_price = models.FloatField(default=1, help_text='Monthly price (e.g. 1, 2, 3, ...)')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text='Currency')

    how_many_months = models.IntegerField(
        default=1, help_text='How many months and installments to collect (e.g. 1, 2, 3, ...)')

    def clean(self) -> None:
        if not self.monthly_price:
            raise forms.ValidationError(
                translation(self._lang,
                            en='Monthly price is required',
                            es='El precio mensual es requerido',
                            slug='monthly-price-required'))

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.monthly_price} {self.currency.code} per {self.how_many_months} months'


class MentorshipServiceSet(models.Model):
    """
    M2M between plan and ServiceItem
    """

    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text='A human-readable identifier, it must be unique and it can only contain letters, '
        'numbers and hyphens')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    mentorship_services = models.ManyToManyField(MentorshipService, blank=True)


class MentorshipServiceSetTranslation(models.Model):
    mentorship_service_set = models.ForeignKey(MentorshipServiceSet,
                                               on_delete=models.CASCADE,
                                               help_text='Mentorship service set')
    lang = models.CharField(max_length=5,
                            validators=[validate_language_code],
                            help_text='ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US')
    title = models.CharField(max_length=60, help_text='Title of the mentorship service set')
    description = models.CharField(max_length=255, help_text='Description of the mentorship service set')
    short_description = models.CharField(max_length=255,
                                         help_text='Short description of the mentorship service set')


class EventTypeSet(models.Model):
    """
    M2M between plan and ServiceItem
    """

    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text='A human-readable identifier, it must be unique and it can only contain letters, '
        'numbers and hyphens')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, help_text='Academy owner')
    event_types = models.ManyToManyField(EventType, blank=True, help_text='Event types')


class EventTypeSetTranslation(models.Model):
    event_type_set = models.ForeignKey(EventTypeSet, on_delete=models.CASCADE, help_text='Event type set')
    lang = models.CharField(max_length=5,
                            validators=[validate_language_code],
                            help_text='ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US')
    title = models.CharField(max_length=60, help_text='Title of the event type set')
    description = models.CharField(max_length=255, help_text='Description of the event type set')
    short_description = models.CharField(max_length=255, help_text='Short description of the event type set')


class AcademyService(models.Model):
    service = models.OneToOneField(Service, on_delete=models.CASCADE, help_text='Service')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, help_text='Academy')

    price_per_unit = models.FloatField(default=1, help_text='Price per unit (e.g. 1, 2, 3, ...)')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text='Currency')

    cohort_patterns = models.JSONField(
        default=[], blank=True, help_text='Array of cohort patterns to find cohorts to be sold in this plan')

    available_cohorts = models.ManyToManyField(
        Cohort, blank=True, help_text='Available cohorts to be sold in this this service and plan')

    available_mentorship_service_sets = models.ManyToManyField(
        MentorshipServiceSet,
        blank=True,
        help_text='Available mentorship service sets to be sold in this service and plan')

    available_event_type_sets = models.ManyToManyField(
        EventTypeSet,
        blank=True,
        help_text='Available mentorship service sets to be sold in this service and plan')

    def __str__(self) -> str:
        return f'{self.academy.slug} -> {self.service.slug}'

    def clean(self) -> None:
        if self.id and len([
                x for x in [
                    self.available_cohorts.count(),
                    self.available_mentorship_service_sets.count(),
                    self.available_event_type_sets.count()
                ] if x
        ]) > 1:
            raise forms.ValidationError('Only one of available_cohorts, available_mentorship_service_sets or '
                                        'available_event_type_sets can be set')

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        return super().save(*args, **kwargs)


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

    slug = models.CharField(
        max_length=60,
        unique=True,
        help_text='A human-readable identifier, it must be unique and it can only contain letters, '
        'numbers and hyphens')
    financing_options = models.ManyToManyField(FinancingOption,
                                               blank=True,
                                               help_text='Available financing options')

    is_renewable = models.BooleanField(
        default=True,
        help_text='Is if true, it will create a reneweval subscription instead of a plan financing')

    status = models.CharField(max_length=12, choices=PLAN_STATUS, default=DRAFT, help_text='Status')

    time_of_life = models.IntegerField(default=1,
                                       blank=True,
                                       null=True,
                                       help_text='Timelife of plan (e.g. 1, 2, 3, ...)')
    time_of_life_unit = models.CharField(max_length=10,
                                         choices=PAY_EVERY_UNIT,
                                         blank=True,
                                         null=True,
                                         default=MONTH,
                                         help_text='Timelife unit (e.g. DAY, WEEK, MONTH or YEAR)')

    trial_duration = models.IntegerField(default=1, help_text='Trial duration (e.g. 1, 2, 3, ...)')
    trial_duration_unit = models.CharField(max_length=10,
                                           choices=PAY_EVERY_UNIT,
                                           default=MONTH,
                                           help_text='Trial duration unit (e.g. DAY, WEEK, MONTH or YEAR)')

    service_items = models.ManyToManyField(ServiceItem,
                                           blank=True,
                                           through='PlanServiceItem',
                                           through_fields=('plan', 'service_item'))

    owner = models.ForeignKey(Academy,
                              on_delete=models.CASCADE,
                              blank=True,
                              null=True,
                              help_text='Academy owner')
    is_onboarding = models.BooleanField(default=False, help_text='Is onboarding plan?')
    has_waiting_list = models.BooleanField(default=False, help_text='Has waiting list?')

    # patterns
    cohort_pattern = models.CharField(max_length=80,
                                      default=None,
                                      blank=True,
                                      null=True,
                                      help_text='Cohort pattern to find cohorts to be sold in this plan')

    available_cohorts = models.ManyToManyField(
        Cohort, blank=True, help_text='Available cohorts to be sold in this this service and plan')

    mentorship_service_set = models.ForeignKey(
        MentorshipServiceSet,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        help_text='Mentorship service sets to be sold in this service and plan')

    event_type_set = models.ForeignKey(EventTypeSet,
                                       on_delete=models.SET_NULL,
                                       blank=True,
                                       null=True,
                                       default=None,
                                       help_text='Event type sets to be sold in this service and plan')

    def __str__(self) -> str:
        return self.slug

    def clean(self) -> None:
        if not self.is_renewable and (not self.time_of_life or not self.time_of_life_unit):
            raise forms.ValidationError(
                'If the plan is not renewable, you must set time_of_life and time_of_life_unit')

        if self.is_renewable and (self.time_of_life or self.time_of_life_unit):
            raise forms.ValidationError(
                'If the plan is renewable, you must not set time_of_life and time_of_life_unit')

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()

        super().save(*args, **kwargs)


class PlanTranslation(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    lang = models.CharField(max_length=5,
                            validators=[validate_language_code],
                            help_text='ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US')
    title = models.CharField(max_length=60, help_text='Title of the plan')
    description = models.CharField(max_length=255, help_text='Description of the plan')

    def save(self):
        self.full_clean()

        super().save()

    def __str__(self) -> str:
        return f'{self.lang} {self.title}: ({self.plan.slug})'


class PlanOffer(models.Model):
    original_plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='plan_offer_from')
    suggested_plan = models.ForeignKey(Plan,
                                       related_name='plan_offer_to',
                                       help_text='Suggested plans',
                                       null=True,
                                       blank=False,
                                       on_delete=models.CASCADE)
    show_modal = models.BooleanField(default=False)
    expires_at = models.DateTimeField(default=None, blank=True, null=True)

    def clean(self) -> None:
        utc_now = timezone.now()
        others = self.__class__.objects.filter(Q(expires_at=None) | Q(expires_at__gt=utc_now),
                                               original_plan=self.original_plan)

        if self.pk:
            others = others.exclude(pk=self.pk)

        if others.exists():
            raise forms.ValidationError('There is already an active plan offer for this plan')

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()

        super().save(*args, **kwargs)


class PlanOfferTranslation(models.Model):
    offer = models.ForeignKey(PlanOffer, on_delete=models.CASCADE, help_text='Plan offer')
    lang = models.CharField(max_length=5,
                            validators=[validate_language_code],
                            help_text='ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US')
    title = models.CharField(max_length=60, help_text='Title of the plan offer')
    description = models.CharField(max_length=255, help_text='Description of the plan offer')
    short_description = models.CharField(max_length=255, help_text='Short description of the plan offer')


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

    status = models.CharField(max_length=8, choices=BAG_STATUS, default=CHECKING, help_text='Bag status')
    type = models.CharField(max_length=7, choices=BAG_TYPE, default=BAG, help_text='Bag type')
    chosen_period = models.CharField(
        max_length=7,
        choices=CHOSEN_PERIOD,
        default=NO_SET,
        help_text='Chosen period used to calculate the amount and build the subscription')
    how_many_installments = models.IntegerField(
        default=0, help_text='How many installments to collect and build the plan financing')

    academy = models.ForeignKey('admissions.Academy', on_delete=models.CASCADE, help_text='Academy owner')
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text='Customer')
    service_items = models.ManyToManyField(ServiceItem, blank=True, help_text='Service items')
    plans = models.ManyToManyField(Plan, blank=True, help_text='Plans')
    selected_cohorts = models.ManyToManyField('admissions.Cohort',
                                              blank=True,
                                              help_text='Selected cohorts for the plans of services')

    selected_mentorship_service_sets = models.ManyToManyField(
        MentorshipServiceSet,
        blank=True,
        help_text='Selected mentorship service sets for the plans of services')

    selected_event_type_sets = models.ManyToManyField(
        EventTypeSet, blank=True, help_text='Selected event type sets for the plans of services')

    is_recurrent = models.BooleanField(default=False, help_text='will it be a recurrent payment?')
    was_delivered = models.BooleanField(default=False, help_text='Was it delivered to the user?')

    token = models.CharField(max_length=40,
                             db_index=True,
                             default=None,
                             null=True,
                             blank=True,
                             help_text='Token of the bag')
    expires_at = models.DateTimeField(
        default=None,
        blank=True,
        null=True,
        help_text='Expiration date of the bag, used for preview bag together with the token')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self):
        settings = get_user_settings(self.user.id)
        if self.id and self.selected_cohorts.count() > 1:
            raise forms.ValidationError(
                translation(settings.lang,
                            en='You can only select one cohort per bag',
                            es='Solo puedes seleccionar un cohorte por bolsa'))

        if self.id and self.selected_mentorship_service_sets.count() > 1:
            raise forms.ValidationError(
                translation(settings.lang,
                            en='You can only select one mentorship service set per bag',
                            es='Solo puedes seleccionar un conjunto de servicios de mentoría por bolsa'))

        if self.id and self.selected_event_type_sets.count() > 1:
            raise forms.ValidationError(
                translation(settings.lang,
                            en='You can only select one event type set per bag',
                            es='Solo puedes seleccionar un conjunto de tipos de evento por bolsa'))

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
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text='Currency of the invoice')
    paid_at = models.DateTimeField(help_text='Date when the invoice was paid')
    refunded_at = models.DateTimeField(null=True,
                                       blank=True,
                                       default=None,
                                       help_text='Date when the invoice was refunded')
    status = models.CharField(max_length=17,
                              choices=INVOICE_STATUS,
                              default=PENDING,
                              help_text='Invoice status')

    bag = models.ForeignKey('Bag', on_delete=models.CASCADE, help_text='Bag')

    # actually return 27 characters
    stripe_id = models.CharField(max_length=32, null=True, default=None, blank=True, help_text='Stripe id')

    # actually return 27 characters
    refund_stripe_id = models.CharField(max_length=32,
                                        null=True,
                                        default=None,
                                        blank=True,
                                        help_text='Stripe id for refunding')

    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text='Customer')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, help_text='Academy owner')

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
EXPIRED = 'EXPIRED'
SUBSCRIPTION_STATUS = [
    (FREE_TRIAL, 'Free trial'),
    (ACTIVE, 'Active'),
    (CANCELLED, 'Cancelled'),
    (DEPRECATED, 'Deprecated'),
    (PAYMENT_ISSUE, 'Payment issue'),
    (ERROR, 'Error'),
    (FULLY_PAID, 'Fully Paid'),
    (EXPIRED, 'Expired'),
]


class AbstractIOweYou(models.Model):
    """
    Common fields for all I owe you.
    """

    status = models.CharField(max_length=13, choices=SUBSCRIPTION_STATUS, default=ACTIVE, help_text='Status')
    status_message = models.CharField(max_length=250,
                                      null=True,
                                      blank=True,
                                      default=None,
                                      help_text='Error message if status is ERROR')

    invoices = models.ManyToManyField(Invoice, blank=True, help_text='Invoices')

    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text='Customer')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, help_text='Academy owner')

    selected_cohort = models.ForeignKey(Cohort,
                                        on_delete=models.CASCADE,
                                        null=True,
                                        blank=True,
                                        default=None,
                                        help_text='Cohort which the plans and services is for')
    selected_mentorship_service_set = models.ForeignKey(
        MentorshipServiceSet,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        help_text='Mentorship service set which the plans and services is for')
    selected_event_type_set = models.ForeignKey(
        EventTypeSet,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        help_text='Event type set which the plans and services is for')

    # this reminds the plans to change the stock scheduler on change
    plans = models.ManyToManyField(Plan, blank=True, help_text='Plans to be suplied')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class PlanFinancing(AbstractIOweYou):
    """
    Allows to financing a plan
    """

    # in this day the financing needs being paid again
    next_payment_at = models.DateTimeField(help_text='Next payment date')

    # in this moment the subscription will be expired
    valid_until = models.DateTimeField(
        help_text='Valid until, before this date each month the customer must pay, after this '
        'date the plan financing will be destroyed and if it is belonging to a cohort, the certificate will '
        'be issued after pay every installments')

    # in this moment the subscription will be expired
    plan_expires_at = models.DateTimeField(
        default=None,
        null=True,
        blank=False,
        help_text='Plan expires at, after this date the plan will not be renewed')

    # this remember the current price per month
    monthly_price = models.FloatField(
        default=0, help_text='Monthly price, we keep this to avoid we changes him/her amount')

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


class Subscription(AbstractIOweYou):
    """
    Allows to create a subscription to a plan and services.
    """

    _lang = 'en'

    # last time the subscription was paid
    paid_at = models.DateTimeField(help_text='Last time the subscription was paid')

    is_refundable = models.BooleanField(default=True, help_text='Is it refundable?')

    # in this day the subscription needs being paid again
    next_payment_at = models.DateTimeField(help_text='Next payment date')

    # in this moment the subscription will be expired
    valid_until = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
        help_text='Valid until, after this date the subscription will be destroyed')

    # this reminds the service items to change the stock scheduler on change
    # only for consuming single items without having a plan, when you buy consumable quantities
    service_items = models.ManyToManyField(ServiceItem,
                                           blank=True,
                                           through='SubscriptionServiceItem',
                                           through_fields=('subscription', 'service_item'),
                                           help_text='Service items to be suplied')

    # remember the chosen period to pay again
    pay_every = models.IntegerField(default=1, help_text='Pay every X units (e.g. 1, 2, 3, ...)')
    pay_every_unit = models.CharField(max_length=10,
                                      choices=PAY_EVERY_UNIT,
                                      default=MONTH,
                                      help_text='Pay every unit (e.g. DAY, WEEK, MONTH or YEAR)')

    def __str__(self) -> str:
        return f'{self.user.email} ({self.valid_until})'

    def clean(self) -> None:
        if self.status == 'FULLY_PAID':
            raise forms.ValidationError(
                translation(self._lang,
                            en='Subscription cannot have fully paid as status',
                            es='La suscripción no puede tener pagado como estado',
                            slug='subscription-as-fully-paid'))

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        return super().save(*args, **kwargs)


class SubscriptionServiceItem(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, help_text='Subscription')
    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE, help_text='Service item')

    cohorts = models.ManyToManyField(Cohort, blank=True, help_text='Cohorts')
    mentorship_service_set = models.ForeignKey(MentorshipServiceSet,
                                               on_delete=models.CASCADE,
                                               blank=True,
                                               null=True,
                                               help_text='Mentorship service set')

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


class Consumable(AbstractServiceItem):
    """
    This model is used to represent the units of a service that can be consumed.
    """

    service_item = models.ForeignKey(
        ServiceItem,
        on_delete=models.CASCADE,
        help_text='Service item, we remind the service item to know how many units was issued')

    # if null, this is valid until resources are exhausted
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text='Customer')

    # this could be used for the queries on the consumer, to recognize which resource is belong the consumable
    cohort = models.ForeignKey(Cohort,
                               on_delete=models.CASCADE,
                               default=None,
                               blank=True,
                               null=True,
                               help_text='Cohort which the consumable belongs to')
    event_type_set = models.ForeignKey(EventTypeSet,
                                       on_delete=models.CASCADE,
                                       default=None,
                                       blank=True,
                                       null=True,
                                       help_text='Event type which the consumable belongs to')
    mentorship_service_set = models.ForeignKey(MentorshipServiceSet,
                                               on_delete=models.CASCADE,
                                               default=None,
                                               blank=True,
                                               null=True,
                                               help_text='Mentorship service which the consumable belongs to')

    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text='Valid until, this is null if the consumable is valid until resources are exhausted')

    def clean(self) -> None:
        resources = [self.cohort]

        if self.id:
            resources += [self.event_type_set, self.mentorship_service_set]

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
    consumable = models.ForeignKey(Consumable, on_delete=models.CASCADE, help_text='Consumable')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, help_text='Customer')
    eta = models.DateTimeField(help_text='Estimated time of arrival')
    duration = models.DurationField(blank=False, default=timedelta, help_text='Duration of the session')
    how_many = models.FloatField(default=0, help_text='How many units of this service can be used')
    status = models.CharField(max_length=12,
                              choices=CONSUMPTION_SESSION_STATUS,
                              default=PENDING,
                              help_text='Status of the session')
    was_discounted = models.BooleanField(default=False, help_text='Was it discounted')

    request = models.JSONField(
        default=dict,
        blank=True,
        help_text='Request parameters, it\'s used to remind and recover and consumption session')

    # this should be used to get
    path = models.CharField(max_length=200, blank=True, help_text='Path of the request')
    related_id = models.IntegerField(default=None, blank=True, null=True, help_text='Related id')
    related_slug = models.CharField(
        max_length=200,
        default=None,
        blank=True,
        null=True,
        help_text='Related slug, it\'s human-readable identifier, it must be unique and it can only contain '
        'letters, numbers and hyphens')

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

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, help_text='Plan')
    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE, help_text='Service item')


class PlanServiceItemHandler(models.Model):
    """
    M2M between plan and ServiceItem
    """

    handler = models.ForeignKey(PlanServiceItem, on_delete=models.CASCADE, help_text='Plan service item')

    # resources associated to this service item, one is required
    subscription = models.ForeignKey(Subscription,
                                     on_delete=models.CASCADE,
                                     null=True,
                                     blank=True,
                                     default=None,
                                     help_text='Subscription')
    plan_financing = models.ForeignKey(PlanFinancing,
                                       on_delete=models.CASCADE,
                                       null=True,
                                       blank=True,
                                       default=None,
                                       help_text='Plan financing')

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
                                             null=True,
                                             help_text='Subscription service item')
    plan_handler = models.ForeignKey(PlanServiceItemHandler,
                                     on_delete=models.CASCADE,
                                     default=None,
                                     blank=True,
                                     null=True,
                                     help_text='Plan service item handler')

    # this reminds which scheduler generated the consumable
    consumables = models.ManyToManyField(Consumable, blank=True, help_text='Consumables')
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text='Valid until, after this date the consumables will be renewed')

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
    user = models.OneToOneField(User,
                                on_delete=models.CASCADE,
                                related_name='payment_contact',
                                help_text='Customer')
    stripe_id = models.CharField(max_length=20, help_text='Stripe id')  # actually return 18 characters

    def __str__(self) -> str:
        return f'{self.user.email} ({self.stripe_id})'


class FinancialReputation(models.Model):
    """
    The purpose of this model is to store the reputation of a user, if the user has a bad reputation, the
    user will not be able to buy services.
    """

    user = models.OneToOneField(User,
                                on_delete=models.CASCADE,
                                related_name='reputation',
                                help_text='Customer')

    in_4geeks = models.CharField(max_length=17,
                                 choices=INVOICE_STATUS,
                                 default=GOOD,
                                 help_text='4Geeks reputation')
    in_stripe = models.CharField(max_length=17,
                                 choices=INVOICE_STATUS,
                                 default=GOOD,
                                 help_text='Stripe reputation')

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

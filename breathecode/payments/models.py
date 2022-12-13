import ast
import os
from django.contrib.auth.models import Group, User
from django.db import models

from breathecode.admissions.models import DRAFT, Academy, Cohort, Country
from breathecode.events.models import EventType
from breathecode.authenticate.actions import get_user_settings
from breathecode.mentorship.models import MentorshipService
from currencies import Currency as CurrencyFormatter

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

    price_per_month = models.FloatField(default=0)
    price_per_quarter = models.FloatField(default=0)
    price_per_half = models.FloatField(default=0)
    price_per_year = models.FloatField(default=0)
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


class PaymentServiceScheduler(models.Model):
    _lang = 'en'
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    # patterns
    cohort_pattern = models.CharField(max_length=80, default=None, blank=True, null=True)
    # mentorship_service_pattern = models.CharField(max_length=80, default=None, blank=True, null=True)

    # this is used for the renovations of credits
    renew_every = models.IntegerField(default=1)
    renew_every_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    # section of cache, is a nightmare solve this problem without it
    cohorts = models.ManyToManyField(Cohort, blank=True)
    mentorship_services = models.ManyToManyField(MentorshipService, blank=True)

    def _how_many(self):
        how_many = 0
        if self.cohort_pattern:
            how_many += 1

        # if self.mentorship_service_pattern:
        #     how_many += 1

        return how_many

    # def set_language(self, lang):
    #     self._lang = lang

    # def set_language_from_settings(self, settings):
    #     self._lang = settings.lang

    @property
    def cohort_regex(self):
        if not self.cohort_pattern:
            return None

        return ast.literal_eval(self.cohort_pattern)

    # @property
    # def mentorship_service_regex(self):
    #     if not self.mentorship_service_pattern:
    #         return None

    #     return ast.literal_eval(self.mentorship_service_pattern)

    def save(self):
        # if self._how_many() > 1:
        #     raise Exception(
        #         translation(self._lang,
        #                     en='You can only set one regex per fixture',
        #                     es='Solo puede establecer una expresión regular por fixture'))

        self.full_clean()

        super().save()


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

    def save(self, *args, **kwargs):
        is_test_env = os.getenv('ENV') == 'test'
        inside_mixer = hasattr(self, '__mixer__')
        if self.id and (not inside_mixer or (inside_mixer and not is_test_env)):
            raise Exception('You cannot update a service item')

        self.full_clean()

        super().save()

    def delete(self):
        raise Exception('You cannot delete a service item')


class FinancingOption(models.Model):
    """
    This model is used as referenced of units of a service can be used.
    """

    monthly_price = models.IntegerField(default=1)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)

    how_many_months = models.IntegerField(default=1)


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
    financing_options = models.ManyToManyField(FinancingOption, blank=True)

    status = models.CharField(max_length=12, choices=PLAN_STATUS, default=DRAFT)
    #TODO: visible enum, private, unlisted, visible

    pay_every = models.IntegerField(default=1)
    pay_every_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    trial_duration = models.IntegerField(default=1)
    trial_duration_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)

    service_items = models.ManyToManyField(ServiceItem,
                                           blank=True,
                                           through='PlanServiceItem',
                                           through_fields=('plan', 'service_item'))

    owner = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True)
    is_onboarding = models.BooleanField(default=False)


class PlanTranslation(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    lang = models.CharField(max_length=5, validators=[validate_language_code])
    title = models.CharField(max_length=60)
    description = models.CharField(max_length=255)

    def save(self):
        self.full_clean()

        super().save()


# class Balance:
#     id: int
#     slug: int
#     how_many: int

# class MentorshipServiceSet:
#     mentorship_services = models.ForeignKey(User, on_delete=models.CASCADE)


class Consumable(AbstractServiceItem):
    """
    This model is used to represent the units of a service that can be consumed.
    """

    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE)

    # if null, this is valid until resources are exhausted
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # this could be used for the queries on the consumer, to recognize which resource is belong the consumable
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, default=None, blank=True, null=True)
    event_type = models.ForeignKey(EventType, on_delete=models.CASCADE, default=None, blank=True, null=True)
    mentorship_service = models.ForeignKey(MentorshipService,
                                           on_delete=models.CASCADE,
                                           default=None,
                                           blank=True,
                                           null=True)

    # if null, this is valid until resources are exhausted
    valid_until = models.DateTimeField(null=True, blank=True, default=None)

    def clean(self) -> None:
        resources = [self.cohort, self.mentorship_service, self.event_type]
        how_many_resources_are_set = len([r for r in resources if r is not None])

        settings = get_user_settings(self.user.id)

        if how_many_resources_are_set > 1:
            raise Exception(
                translation(settings.lang,
                            en='A consumable can only be associated with one resource',
                            es='Un consumible solo se puede asociar con un recurso'))

        if not self.service_item:
            raise Exception(
                translation(settings.lang,
                            en='A consumable must be associated with a service item',
                            es='Un consumible debe estar asociado con un artículo de un servicio'))

        return super().clean()

    def save(self):
        self.full_clean()

        super().save()

    def __str__(self):
        return f'{self.service_item.service.slug} {self.how_many}'


RENEWAL = 'RENEWAL'
CHECKING = 'CHECKING'
PAID = 'PAID'
BAG_STATUS = [
    (RENEWAL, 'Renewal'),
    (CHECKING, 'Checking'),
    (PAID, 'Paid'),
]

BAG = 'BAG'
PREVIEW = 'PREVIEW'
BAG_TYPE = [
    (BAG, 'Bag'),
    (PREVIEW, 'Preview'),
]

QUARTER = 'QUARTER'
HALF = 'HALF'
YEAR = 'YEAR'
CHOSEN_PERIOD = [
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
    chosen_period = models.CharField(max_length=7, choices=CHOSEN_PERIOD, default=MONTH)

    academy = models.ForeignKey('admissions.Academy', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service_items = models.ManyToManyField(ServiceItem, blank=True)
    plans = models.ManyToManyField(Plan, blank=True)

    is_recurrent = models.BooleanField(default=False)
    was_delivered = models.BooleanField(default=False)

    token = models.CharField(max_length=40, db_index=True, default=None, null=True, blank=True)
    expires_at = models.DateTimeField(default=None, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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
    status = models.CharField(max_length=17, choices=INVOICE_STATUS, default=PENDING)

    bag = models.ForeignKey('Bag', on_delete=models.CASCADE)

    # actually return 27 characters
    stripe_id = models.CharField(max_length=32, null=True, default=None, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)


FREE_TRIAL = 'FREE_TRIAL'
ACTIVE = 'ACTIVE'
CANCELLED = 'CANCELLED'
DEPRECATED = 'DEPRECATED'
PAYMENT_ISSUE = 'PAYMENT_ISSUE'
ERROR = 'ERROR'
SUBSCRIPTION_STATUS = [
    (FREE_TRIAL, 'Free trial'),
    (ACTIVE, 'Active'),
    (CANCELLED, 'Cancelled'),
    (DEPRECATED, 'Deprecated'),
    (PAYMENT_ISSUE, 'Payment issue'),
    (ERROR, 'Error'),
]


class AbstractIOweYou(models.Model):
    """
    Common fields for all I owe you.
    """

    status = models.CharField(max_length=13, choices=SUBSCRIPTION_STATUS, default=ACTIVE)
    status_message = models.CharField(max_length=150, null=True, blank=True, default=None)

    invoices = models.ManyToManyField(Invoice, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

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
    valid_until = models.DateTimeField()

    # this reminds the service items to change the stock scheduler on change
    service_items = models.ManyToManyField(ServiceItem,
                                           blank=True,
                                           through='SubscriptionServiceItem',
                                           through_fields=('subscription', 'service_item'))

    # remember the chosen period to pay again
    pay_every = models.IntegerField(default=1)
    pay_every_unit = models.CharField(max_length=10, choices=PAY_EVERY_UNIT, default=MONTH)


class SubscriptionServiceItem(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE)


class PlanFinancing(AbstractIOweYou):
    """
    Allows to financing a plan
    """

    # last time the subscription was paid
    paid_at = models.DateTimeField()

    # in this day the subscription needs being paid again
    pay_until = models.DateTimeField()


class PlanServiceItem(models.Model):
    """
    M2M between plan and ServiceItem
    """

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)


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
            raise Exception('A PlanServiceItem must be associated with one resource')

        if how_many_resources_are_set != 1:
            raise Exception('A PlanServiceItem can only be associated with one resource')

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)


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

    last_renew = models.DateTimeField(null=True, blank=True, default=None)

    # valid_until = models.DateTimeField(null=True, blank=False, default=None)

    def clean(self) -> None:
        resources = [self.subscription_handler, self.plan_handler]
        how_many_resources_are_set = len([r for r in resources if r is not None])

        if how_many_resources_are_set == 0:
            raise Exception('A ServiceStockScheduler must be associated with one resource')

        if how_many_resources_are_set != 1:
            raise Exception('A ServiceStockScheduler can only be associated with one resource')

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)


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

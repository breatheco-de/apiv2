from __future__ import annotations

import logging
import math
import os
from datetime import timedelta
from typing import Any, Optional

from asgiref.sync import sync_to_async
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from currencies import Currency as CurrencyFormatter
from django import forms
from django.contrib.auth.models import Group, Permission, User
from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from django.db.models import Q, QuerySet
from django.utils import timezone

import breathecode.activity.tasks as tasks_activity
from breathecode.admissions.models import Academy, Cohort, Country
from breathecode.authenticate.actions import get_user_settings
from breathecode.authenticate.models import UserInvite
from breathecode.events.models import EventType
from breathecode.mentorship.models import MentorshipService
from breathecode.payments import signals
from breathecode.utils.validators.language import validate_language_code

# https://devdocs.prestashop-project.org/1.7/webservice/resources/warehouses/

# ⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇ #
# ↕           Remember do not save the card info in the backend            ↕ #
# ⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆ #

logger = logging.getLogger(__name__)


class Currency(models.Model):
    """Represents a currency."""

    code = models.CharField(
        max_length=3, unique=True, db_index=True, help_text="ISO 4217 currency code (e.g. USD, EUR, MXN)"
    )
    name = models.CharField(max_length=20, unique=True, help_text="Currency name (e.g. US Dollar, Euro, Mexican Peso)")
    decimals = models.IntegerField(default=0, help_text="Number of decimals (e.g. 2 for USD and EUR, 0 for JPY)")

    countries = models.ManyToManyField(
        Country, blank=True, related_name="currencies", help_text="Countries that use this currency officially"
    )

    def format_price(self, value):
        currency = CurrencyFormatter("USD")
        currency.get_money_currency()
        return currency.get_money_format(value)

    def clean(self) -> None:
        self.code = self.code.upper()
        return super().clean()

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class AbstractPriceByUnit(models.Model):
    """This model is used to store the price of a Product or a Service."""

    price_per_unit = models.FloatField(default=0, help_text="Price per unit")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency")

    def format_price(self):
        return self.currency.format_price(self.price)

    class Meta:
        abstract = True


class AbstractPriceByTime(models.Model):
    """This model is used to store the price of a Product or a Service."""

    price_per_month = models.FloatField(default=None, blank=True, null=True, help_text="Price per month")
    price_per_quarter = models.FloatField(default=None, blank=True, null=True, help_text="Price per quarter")
    price_per_half = models.FloatField(default=None, blank=True, null=True, help_text="Price per half")
    price_per_year = models.FloatField(default=None, blank=True, null=True, help_text="Price per year")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency")

    def format_price(self):
        return self.currency.format_price(self.price)

    class Meta:
        abstract = True


class AbstractAmountByTime(models.Model):
    """This model is used to store the price of a Product or a Service."""

    amount_per_month = models.FloatField(default=0, help_text="Amount per month")
    amount_per_quarter = models.FloatField(default=0, help_text="Amount per quarter")
    amount_per_half = models.FloatField(default=0, help_text="Amount per half")
    amount_per_year = models.FloatField(default=0, help_text="Amount per year")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency")

    def format_price(self):
        return self.currency.format_price(self.price)

    class Meta:
        abstract = True


DAY = "DAY"
WEEK = "WEEK"
MONTH = "MONTH"
YEAR = "YEAR"
PAY_EVERY_UNIT = [
    (DAY, "Day"),
    (WEEK, "Week"),
    (MONTH, "Month"),
    (YEAR, "Year"),
]


class AbstractAsset(models.Model):
    """This model represents a product or a service that can be sold."""

    slug = models.CharField(
        max_length=60,
        unique=True,
        db_index=True,
        help_text="A human-readable identifier, it must be unique and it can only contain letters, "
        "numbers and hyphens",
    )

    title = models.CharField(max_length=60, default=None, null=True, blank=True)

    owner = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True, help_text="Academy owner")
    # TODO: visibility and the capacities of disable a asset
    private = models.BooleanField(default=True, help_text="If the asset is private or not", db_index=True)

    trial_duration = models.IntegerField(default=1, help_text="Trial duration (e.g. 1, 2, 3, ...)")
    trial_duration_unit = models.CharField(
        max_length=10,
        choices=PAY_EVERY_UNIT,
        default=MONTH,
        help_text="Trial duration unit (e.g. DAY, WEEK, MONTH or YEAR)",
    )

    icon_url = models.URLField(blank=True, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class Service(AbstractAsset):
    """Represents the service that can be purchased by the customer."""

    class Type(models.TextChoices):
        COHORT_SET = ("COHORT_SET", "Cohort set")
        MENTORSHIP_SERVICE_SET = ("MENTORSHIP_SERVICE_SET", "Mentorship service set")
        EVENT_TYPE_SET = ("EVENT_TYPE_SET", "Event type set")
        VOID = ("VOID", "Void")

    class Consumer(models.TextChoices):
        ADD_CODE_REVIEW = ("ADD_CODE_REVIEW", "Add code review")
        LIVE_CLASS_JOIN = ("LIVE_CLASS_JOIN", "Live class join")
        EVENT_JOIN = ("EVENT_JOIN", "Event join")
        JOIN_MENTORSHIP = ("JOIN_MENTORSHIP", "Join mentorship")
        READ_LESSON = ("READ_LESSON", "Read lesson")
        AI_INTERACTION = ("AI_INTERACTION", "AI Interaction")
        NO_SET = ("NO_SET", "No set")

    groups = models.ManyToManyField(
        Group, blank=True, help_text="Groups that can access the customer that bought this service"
    )

    session_duration = models.DurationField(
        default=None, null=True, blank=True, help_text="Session duration, used in consumption sessions"
    )
    type = models.CharField(max_length=22, choices=Type, default=Type.COHORT_SET, help_text="Service type")
    consumer = models.CharField(max_length=15, choices=Consumer, default=Consumer.NO_SET, help_text="Service type")

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)


class ServiceTranslation(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, help_text="Service")
    lang = models.CharField(
        max_length=5,
        validators=[validate_language_code],
        help_text="ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US",
    )
    title = models.CharField(max_length=60, help_text="Title of the service")
    description = models.CharField(max_length=255, help_text="Description of the service")

    def __str__(self) -> str:
        return f"{self.lang}: {self.title}"


UNIT = "UNIT"
SERVICE_UNITS = [
    (UNIT, "Unit"),
]


class AbstractServiceItem(models.Model):
    """Common fields for ServiceItem and Consumable."""

    # the unit between a service and a product are different
    unit_type = models.CharField(
        max_length=10, choices=SERVICE_UNITS, default=UNIT, db_index=True, help_text="Unit type (e.g. UNIT))"
    )
    how_many = models.IntegerField(default=-1, help_text="How many units of this service can be used")
    sort_priority = models.IntegerField(
        default=1, help_text="(e.g. 1, 2, 3, ...) It is going to be used to sort the items on the frontend"
    )

    class Meta:
        abstract = True


# this class is used as referenced of units of a service can be used
class ServiceItem(AbstractServiceItem):
    """This model is used as referenced of units of a service can be used."""

    service = models.ForeignKey(Service, on_delete=models.CASCADE, help_text="Service")
    is_renewable = models.BooleanField(
        default=False,
        help_text="If it's marked, the consumables will be renewed according to the renew_at and renew_at_unit values.",
    )

    # the below fields are useless when is_renewable=False
    renew_at = models.IntegerField(
        default=1, help_text="Renew at (e.g. 1, 2, 3, ...) it going to be used to build the balance of " "customer"
    )
    renew_at_unit = models.CharField(
        max_length=10, choices=PAY_EVERY_UNIT, default=MONTH, help_text="Renew at unit (e.g. DAY, WEEK, MONTH or YEAR)"
    )

    def clean(self):
        is_test_env = os.getenv("ENV") == "test"
        inside_mixer = hasattr(self, "__mixer__")
        if self.id and (not inside_mixer or (inside_mixer and not is_test_env)):
            raise forms.ValidationError("You cannot update a service item")

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def delete(self):
        raise forms.ValidationError("You cannot delete a service item")

    def __str__(self) -> str:
        return f"{self.service.slug} ({self.how_many})"


class ServiceItemFeature(models.Model):
    """This model is used as referenced of units of a service can be used."""

    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE, help_text="Service item")
    lang = models.CharField(
        max_length=5,
        validators=[validate_language_code],
        help_text="ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US",
    )
    title = models.CharField(max_length=64, help_text="Title of the service item", default=None, null=True)
    description = models.CharField(max_length=255, help_text="Description of the service item")
    one_line_desc = models.CharField(max_length=64, help_text="One line description of the service item")

    def __str__(self) -> str:
        return f"{self.lang} {self.service_item.service.slug} ({self.service_item.how_many})"


class FinancingOption(models.Model):
    """This model is used as referenced of units of a service can be used."""

    _lang = "en"

    monthly_price = models.FloatField(default=1, help_text="Monthly price (e.g. 1, 2, 3, ...)")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency")

    pricing_ratio_exceptions = models.JSONField(
        default=dict, blank=True, help_text="Exceptions to the general pricing ratios per country"
    )

    how_many_months = models.IntegerField(
        default=1, help_text="How many months and installments to collect (e.g. 1, 2, 3, ...)"
    )

    def clean(self) -> None:
        if not self.monthly_price:
            raise forms.ValidationError(
                translation(
                    self._lang,
                    en="Monthly price is required",
                    es="El precio mensual es requerido",
                    slug="monthly-price-required",
                )
            )

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.monthly_price} {self.currency.code} per {self.how_many_months} months"


class CohortSet(models.Model):
    """Cohort set."""

    _lang = "en"

    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="A human-readable identifier, it must be unique and it can only contain letters, "
        "numbers and hyphens",
    )
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    cohorts = models.ManyToManyField(
        Cohort, blank=True, through="CohortSetCohort", through_fields=("cohort_set", "cohort")
    )

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        return super().save(*args, **kwargs)


class CohortSetTranslation(models.Model):
    cohort_set = models.ForeignKey(CohortSet, on_delete=models.CASCADE, help_text="Cohort set")
    lang = models.CharField(
        max_length=5,
        validators=[validate_language_code],
        help_text="ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US",
    )
    title = models.CharField(max_length=60, help_text="Title of the cohort set")
    description = models.CharField(max_length=255, help_text="Description of the cohort set")
    short_description = models.CharField(max_length=255, help_text="Short description of the cohort set")


class CohortSetCohort(models.Model):
    """M2M between CohortSet and Cohort."""

    _lang = "en"

    cohort_set = models.ForeignKey(CohortSet, on_delete=models.CASCADE, help_text="Cohort set")
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, help_text="Cohort")

    def clean(self) -> None:
        if self.cohort.available_as_saas is False or (
            self.cohort.available_as_saas == None and self.cohort.academy.available_as_saas is False
        ):
            raise forms.ValidationError(
                translation(
                    self._lang,
                    en="Cohort is not available as SaaS",
                    es="El cohort no está disponible como SaaS",
                    slug="cohort-not-available-as-saas",
                )
            )

        if self.cohort_set.academy != self.cohort.academy:
            raise forms.ValidationError(
                translation(
                    self._lang,
                    en="Cohort and cohort set must be from the same academy",
                    es="El cohort y el cohort set deben ser de la misma academia",
                    slug="cohort-and-cohort-set-must-be-from-the-same-academy",
                )
            )

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        return super().save(*args, **kwargs)


class MentorshipServiceSet(models.Model):
    """M2M between plan and ServiceItem."""

    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="A human-readable identifier, it must be unique and it can only contain letters, "
        "numbers and hyphens",
    )
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    mentorship_services = models.ManyToManyField(MentorshipService, blank=True)


class MentorshipServiceSetTranslation(models.Model):
    mentorship_service_set = models.ForeignKey(
        MentorshipServiceSet, on_delete=models.CASCADE, help_text="Mentorship service set"
    )
    lang = models.CharField(
        max_length=5,
        validators=[validate_language_code],
        help_text="ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US",
    )
    title = models.CharField(max_length=60, help_text="Title of the mentorship service set")
    description = models.CharField(max_length=255, help_text="Description of the mentorship service set")
    short_description = models.CharField(max_length=255, help_text="Short description of the mentorship service set")


class EventTypeSet(models.Model):
    """M2M between plan and ServiceItem."""

    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="A human-readable identifier, it must be unique and it can only contain letters, "
        "numbers and hyphens",
    )
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, help_text="Academy owner")
    event_types = models.ManyToManyField(EventType, blank=True, help_text="Event types")


class EventTypeSetTranslation(models.Model):
    event_type_set = models.ForeignKey(EventTypeSet, on_delete=models.CASCADE, help_text="Event type set")
    lang = models.CharField(
        max_length=5,
        validators=[validate_language_code],
        help_text="ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US",
    )
    title = models.CharField(max_length=60, help_text="Title of the event type set")
    description = models.CharField(max_length=255, help_text="Description of the event type set")
    short_description = models.CharField(max_length=255, help_text="Short description of the event type set")


class AcademyService(models.Model):
    _price: float | None = None
    _max_amount: float | None = None
    _currency: Currency | None = None
    _pricing_ratio_explanation: dict | None = None
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, help_text="Academy")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency")
    service = models.OneToOneField(Service, on_delete=models.CASCADE, help_text="Service")

    price_per_unit = models.FloatField(default=1, help_text="Price per unit (e.g. 1, 2, 3, ...)")
    bundle_size = models.FloatField(
        default=1,
        help_text="Minimum unit size allowed to be bought, example: bundle_size=5, then you are "
        "allowed to buy a minimum of 5 units. Related to the discount ratio",
    )

    max_items = models.FloatField(
        default=1, help_text="How many items can be bought in total, it doesn't matter the bundle size"
    )

    max_amount = models.FloatField(default=1, help_text="Limit total amount, it doesn't matter the bundle size")
    discount_ratio = models.FloatField(default=1, help_text="Will be used when calculated by the final price")

    pricing_ratio_exceptions = models.JSONField(
        default=dict, blank=True, help_text="Exceptions to the general pricing ratios per country"
    )

    available_mentorship_service_sets = models.ManyToManyField(
        MentorshipServiceSet,
        blank=True,
        help_text="Available mentorship service sets to be sold in this service and plan",
    )

    available_event_type_sets = models.ManyToManyField(
        EventTypeSet, blank=True, help_text="Available mentorship service sets to be sold in this service and plan"
    )

    available_cohort_sets = models.ManyToManyField(
        CohortSet, blank=True, help_text="Available cohort sets to be sold in this service and plan"
    )

    def __str__(self) -> str:
        return f"{self.academy.slug} -> {self.service.slug}"

    def validate_transaction(
        self, total_items: float, lang: Optional[str] = "en", country_code: Optional[str] = None
    ) -> None:
        if total_items < self.bundle_size:
            raise ValidationException(
                translation(
                    lang,
                    en=f"The amount of items is too low (min {self.bundle_size})",
                    es=f"La cantidad de elementos es demasiado baja (min {self.bundle_size})",
                    slug="the-amount-of-items-is-too-low",
                ),
                code=400,
            )

        if total_items > self.max_items:
            raise ValidationException(
                translation(
                    lang,
                    en=f"The amount of items is too high (max {self.max_items})",
                    es=f"La cantidad de elementos es demasiado alta (máx {self.max_items})",
                    slug="the-amount-of-items-is-too-high",
                ),
                code=400,
            )

        amount, currency, pricing_ratio_explanation = self.get_discounted_price(total_items, country_code)
        max_amount = self.get_max_amount(country_code)

        if amount > max_amount:
            raise ValidationException(
                translation(
                    lang,
                    en=f"The amount of items is too high (max {max_amount})",
                    es=f"La cantidad de elementos es demasiado alta (máx {max_amount})",
                    slug="the-amount-is-too-high",
                ),
                code=400,
            )

        self._price = amount
        self._currency = currency
        self._pricing_ratio_explanation = pricing_ratio_explanation

    def get_max_amount(self, country_code: Optional[str] = None) -> float:
        if self._max_amount is not None:
            return self._max_amount

        return self.pricing_ratio_exceptions.get(country_code, {}).get("max_amount", self.max_amount)

    def get_discounted_price(
        self, num_items: float, country_code: Optional[str] = None, lang: Optional[str] = "en"
    ) -> tuple[float, Currency, dict]:
        from breathecode.payments.actions import apply_pricing_ratio

        if self._price is not None:
            return self._price, self._currency, self._pricing_ratio_explanation

        total_discount_ratio = 0
        current_discount_ratio = self.discount_ratio
        discount_nerf = 0.1
        max_discount = 0.2

        for n in range(math.floor(num_items / self.bundle_size)):
            if n == 0:
                continue

            total_discount_ratio += current_discount_ratio
            current_discount_ratio -= current_discount_ratio * discount_nerf

        if total_discount_ratio > max_discount:
            total_discount_ratio = max_discount

        adjusted_price_per_unit, ratio, c = apply_pricing_ratio(self.price_per_unit, country_code, self, lang=lang)
        currency = c or self.currency
        pricing_ratio_explanation = {"service_items": []}
        if ratio:
            pricing_ratio_explanation["service_items"].append(
                {"service": self.service.slug, "ratio": ratio, "country": country_code}
            )

        amount = adjusted_price_per_unit * num_items
        discount = amount * total_discount_ratio

        return amount - discount, currency, pricing_ratio_explanation

    def clean(self) -> None:
        if (
            self.id
            and len(
                [
                    x
                    for x in [self.available_mentorship_service_sets.count(), self.available_event_type_sets.count()]
                    if x
                ]
            )
            > 1
        ):
            raise forms.ValidationError(
                "Only one of available_mentorship_service_sets or " "available_event_type_sets must be set"
            )

        required_integer_fields = self.service.type in ["MENTORSHIP_SERVICE_SET", "EVENT_TYPE_SET"]

        if required_integer_fields and not self.bundle_size.is_integer():
            raise forms.ValidationError("bundle_size must be an integer")

        if required_integer_fields and not self.max_items.is_integer():
            raise forms.ValidationError("max_items must be an integer")

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        self._price = None
        self._max_amount = None
        self._currency = None
        self._pricing_ratio_explanation = None
        return super().save(*args, **kwargs)


class Plan(AbstractPriceByTime):
    """A plan is a group of services that can be purchased by a user."""

    class Status(models.TextChoices):
        DRAFT = ("DRAFT", "Draft")
        ACTIVE = ("ACTIVE", "Active")
        UNLISTED = ("UNLISTED", "Unlisted")
        DELETED = ("DELETED", "Deleted")
        DISCONTINUED = ("DISCONTINUED", "Discontinued")

    slug = models.CharField(
        max_length=60,
        unique=True,
        db_index=True,
        help_text="A human-readable identifier, it must be unique and it can only contain letters, "
        "numbers and hyphens",
    )
    financing_options = models.ManyToManyField(FinancingOption, blank=True, help_text="Available financing options")

    is_renewable = models.BooleanField(
        default=True, help_text="Is if true, it will create a renewable subscription instead of a plan financing"
    )

    status = models.CharField(max_length=12, choices=Status, default=Status.DRAFT, help_text="Status")

    time_of_life = models.IntegerField(default=1, blank=True, null=True, help_text="Plan lifetime (e.g. 1, 2, 3, ...)")
    time_of_life_unit = models.CharField(
        max_length=10,
        choices=PAY_EVERY_UNIT,
        blank=True,
        null=True,
        default=MONTH,
        help_text="Lifetime unit (e.g. DAY, WEEK, MONTH or YEAR)",
    )

    trial_duration = models.IntegerField(default=1, help_text="Trial duration (e.g. 1, 2, 3, ...)")
    trial_duration_unit = models.CharField(
        max_length=10,
        choices=PAY_EVERY_UNIT,
        default=MONTH,
        help_text="Trial duration unit (e.g. DAY, WEEK, MONTH or YEAR)",
    )

    service_items = models.ManyToManyField(
        ServiceItem, blank=True, through="PlanServiceItem", through_fields=("plan", "service_item")
    )

    add_ons = models.ManyToManyField(
        AcademyService, blank=True, help_text="Service item bundles that can be purchased with this plan"
    )

    owner = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True, help_text="Academy owner")
    is_onboarding = models.BooleanField(default=False, help_text="Is onboarding plan?", db_index=True)
    has_waiting_list = models.BooleanField(default=False, help_text="Has waiting list?")

    pricing_ratio_exceptions = models.JSONField(
        default=dict, blank=True, help_text="Exceptions to the general pricing ratios per country"
    )

    cohort_set = models.ForeignKey(
        CohortSet,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        help_text="Cohort sets to be sold in this service and plan",
    )

    mentorship_service_set = models.ForeignKey(
        MentorshipServiceSet,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        help_text="Mentorship service set to be sold in this service and plan",
    )

    event_type_set = models.ForeignKey(
        EventTypeSet,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        help_text="Event type set to be sold in this service and plan",
    )

    invites = models.ManyToManyField(UserInvite, blank=True, help_text="Plan's invites", related_name="plans")

    def __str__(self) -> str:
        return self.slug

    def clean(self) -> None:

        if not self.is_renewable and (not self.time_of_life or not self.time_of_life_unit):
            raise forms.ValidationError("If the plan is not renewable, you must set time_of_life and time_of_life_unit")

        have_price = self.price_per_month or self.price_per_year or self.price_per_quarter or self.price_per_half

        if self.is_renewable and have_price and (self.time_of_life or self.time_of_life_unit):
            raise forms.ValidationError(
                "If the plan is renewable and have price, you must not set time_of_life and " "time_of_life_unit"
            )

        free_trial_available = self.trial_duration

        if (
            self.is_renewable
            and not have_price
            and free_trial_available
            and (self.time_of_life or self.time_of_life_unit)
        ):
            raise forms.ValidationError(
                "If the plan is renewable and a have free trial available, you must not set time_of_life "
                "and time_of_life_unit"
            )

        if (
            self.is_renewable
            and not have_price
            and not free_trial_available
            and (not self.time_of_life or not self.time_of_life_unit)
        ):
            raise forms.ValidationError(
                "If the plan is renewable and a not have free trial available, you must set time_of_life "
                "and time_of_life_unit"
            )

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()

        super().save(*args, **kwargs)


class PlanTranslation(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    lang = models.CharField(
        max_length=5,
        validators=[validate_language_code],
        help_text="ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US",
    )
    title = models.CharField(max_length=60, help_text="Title of the plan")
    description = models.CharField(max_length=255, help_text="Description of the plan")

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.lang} {self.title}: ({self.plan.slug})"


class PlanOffer(models.Model):
    original_plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="plan_offer_from")
    suggested_plan = models.ForeignKey(
        Plan,
        related_name="plan_offer_to",
        help_text="Suggested plans",
        null=True,
        blank=False,
        on_delete=models.CASCADE,
    )
    show_modal = models.BooleanField(default=False)
    expires_at = models.DateTimeField(default=None, blank=True, null=True)

    def clean(self) -> None:
        utc_now = timezone.now()
        others = self.__class__.objects.filter(
            Q(expires_at=None) | Q(expires_at__gt=utc_now), original_plan=self.original_plan
        )

        if self.pk:
            others = others.exclude(pk=self.pk)

        if others.exists():
            raise forms.ValidationError("There is already an active plan offer for this plan")

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()

        super().save(*args, **kwargs)


class PlanOfferTranslation(models.Model):
    offer = models.ForeignKey(PlanOffer, on_delete=models.CASCADE, help_text="Plan offer")
    lang = models.CharField(
        max_length=5,
        validators=[validate_language_code],
        help_text="ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US",
    )
    title = models.CharField(max_length=60, help_text="Title of the plan offer")
    description = models.CharField(max_length=255, help_text="Description of the plan offer")
    short_description = models.CharField(max_length=255, help_text="Short description of the plan offer")


class Seller(models.Model):

    class Partner(models.TextChoices):
        INDIVIDUAL = ("INDIVIDUAL", "Individual")
        BUSINESS = ("BUSINESS", "Business")

    name = models.CharField(max_length=30, help_text="Company name or person name")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True, limit_choices_to={"is_active": True}
    )

    type = models.CharField(max_length=13, choices=Partner, default=Partner.INDIVIDUAL, db_index=True)
    is_active = models.BooleanField(default=True, help_text="Is the seller active to be selected?")

    def clean(self) -> None:
        if self.user and self.__class__.objects.filter(user=self.user).count() > 0:
            raise forms.ValidationError("User already registered as seller")

        if len(self.name) < 3:
            raise forms.ValidationError("Name must be at least 3 characters long")

        if self.type == self.Partner.BUSINESS and self.__class__.objects.filter(name=self.name).count() > 0:
            raise forms.ValidationError("Name already registered as seller")

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Coupon(models.Model):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._how_many_offers = self.how_many_offers

    class Discount(models.TextChoices):
        NO_DISCOUNT = ("NO_DISCOUNT", "No discount")
        PERCENT_OFF = ("PERCENT_OFF", "Percent off")
        FIXED_PRICE = ("FIXED_PRICE", "Fixed price")
        HAGGLING = ("HAGGLING", "Haggling")

    class Referral(models.TextChoices):
        NO_REFERRAL = ("NO_REFERRAL", "No referral")
        PERCENTAGE = ("PERCENTAGE", "Percentage")
        FIXED_PRICE = ("FIXED_PRICE", "Fixed price")

    slug = models.SlugField()
    discount_type = models.CharField(max_length=13, choices=Discount, default=Discount.PERCENT_OFF, db_index=True)
    discount_value = models.FloatField(help_text="if type is PERCENT_OFF it's a percentage (range 0-1)")

    referral_type = models.CharField(max_length=13, choices=Referral, default=Referral.NO_REFERRAL, db_index=True)
    referral_value = models.FloatField(help_text="If set, the seller will receive a reward", default=0)

    auto = models.BooleanField(
        default=False, db_index=True, help_text="Automatically apply this coupon (like a special offer)"
    )

    how_many_offers = models.IntegerField(
        default=-1, help_text="if -1 means no limits in the offers provided, if 0 nobody can't use this coupon"
    )

    seller = models.ForeignKey(
        Seller,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        limit_choices_to={"is_active": True},
        help_text="Seller",
    )
    plans = models.ManyToManyField(
        Plan,
        blank=True,
        help_text="Available plans, if refferal type is not NO_REFERRAL it should keep empty, "
        "so, in this case, all plans will be available",
    )

    offered_at = models.DateTimeField(default=None, null=True, blank=True)
    expires_at = models.DateTimeField(default=None, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self) -> None:
        if self.discount_value < 0:
            raise forms.ValidationError("Discount value must be positive")

        if self.referral_value < 0:
            raise forms.ValidationError("Referral value must be positive")

        if self.referral_value != 0 and self.referral_type == self.Referral.NO_REFERRAL:
            raise forms.ValidationError("If referral type is NO_REFERRAL, referral value must be None")

        elif self.referral_value is None:
            raise forms.ValidationError("Referral value must be set if referral status is not NO_REFERRAL")

        available_with_slug = self.__class__.objects.filter(
            Q(expires_at=None) | Q(expires_at__gt=timezone.now()), slug=self.slug
        )

        if self.id:
            available_with_slug = available_with_slug.exclude(id=self.id)

        if available_with_slug.count() > 0:
            raise forms.ValidationError("a valid coupon with this name already exists")

        if self.auto and self.discount_type == self.Discount.NO_DISCOUNT:
            raise forms.ValidationError("If auto is True, discount type must not be NO_DISCOUNT")

        if self._how_many_offers != self.how_many_offers or self.offered_at is None:
            self.offered_at = timezone.now()

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()

        super().save(*args, **kwargs)

        self._how_many_offers = self.how_many_offers

    def __str__(self) -> str:
        return self.slug


def limit_coupon_choices():
    return Q(
        Q(offered_at=None) | Q(offered_at__lte=timezone.now()),
        Q(expires_at=None) | Q(expires_at__gte=timezone.now()),
        Q(how_many_offers=-1) | Q(how_many_offers__gt=0),
    )


def _default_pricing_ratio_explanation():
    """Default empty pricing ratio explanation structure."""
    return {"plans": [], "service_items": []}


class Bag(AbstractAmountByTime):
    """Represents a credit that can be used by a user to use a service."""

    class Status(models.TextChoices):
        RENEWAL = ("RENEWAL", "Renewal")
        CHECKING = ("CHECKING", "Checking")
        PAID = ("PAID", "Paid")
        # UNMANAGED = ("UNMANAGED", "Unmanaged")

    class Type(models.TextChoices):
        BAG = ("BAG", "Bag")
        CHARGE = ("CHARGE", "Charge")
        PREVIEW = ("PREVIEW", "Preview")
        INVITED = ("INVITED", "Invited")

    class ChosenPeriod(models.TextChoices):
        NO_SET = ("NO_SET", "No set")
        MONTH = ("MONTH", "Month")
        QUARTER = ("QUARTER", "Quarter")
        HALF = ("HALF", "Half")
        YEAR = ("YEAR", "Year")

    status = models.CharField(
        max_length=8, choices=Status, default=Status.CHECKING, help_text="Bag status", db_index=True
    )
    type = models.CharField(max_length=7, choices=Type, default=Type.BAG, help_text="Bag type")
    chosen_period = models.CharField(
        max_length=7,
        choices=ChosenPeriod,
        default=ChosenPeriod.NO_SET,
        help_text="Chosen period used to calculate the amount and build the subscription",
    )
    how_many_installments = models.IntegerField(
        default=0, help_text="How many installments to collect and build the plan financing"
    )

    coupons = models.ManyToManyField(
        Coupon, blank=True, help_text="Coupons applied during the sale", limit_choices_to=limit_coupon_choices
    )

    academy = models.ForeignKey("admissions.Academy", on_delete=models.CASCADE, help_text="Academy owner")
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Customer")
    service_items = models.ManyToManyField(ServiceItem, blank=True, help_text="Service items")
    plans = models.ManyToManyField(Plan, blank=True, help_text="Plans")

    is_recurrent = models.BooleanField(default=False, help_text="will it be a recurrent payment?")
    was_delivered = models.BooleanField(default=False, help_text="Was it delivered to the user?")

    pricing_ratio_explanation = models.JSONField(
        default=_default_pricing_ratio_explanation,
        blank=True,
        help_text="Explanation of which exceptions were applied to calculate price",
    )

    token = models.CharField(
        max_length=40, db_index=True, default=None, null=True, blank=True, help_text="Token of the bag"
    )
    expires_at = models.DateTimeField(
        default=None,
        blank=True,
        null=True,
        help_text="Expiration date of the bag, used for preview bag together with the token",
    )

    country_code = models.CharField(
        max_length=2,
        default=None,
        null=True,
        blank=True,
        help_text="Country code used for pricing ratio calculations",
    )
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def save(self, *args, **kwargs):
        created = self.pk is None
        self.full_clean()
        super().save(*args, **kwargs)

        if created:
            tasks_activity.add_activity.delay(
                self.user.id, "bag_created", related_type="payments.Bag", related_id=self.id
            )

    def __str__(self) -> str:
        return f"{self.type} {self.status} {self.chosen_period}"


class PaymentMethod(models.Model):
    """
    Different payment methods of each academy have.
    """

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, blank=True, null=True, help_text="Academy owner")
    title = models.CharField(max_length=120, null=False, blank=False)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency", null=True, blank=True)
    is_credit_card = models.BooleanField(default=False, null=False, blank=False)
    description = models.CharField(max_length=480, help_text="Description of the payment method")
    third_party_link = models.URLField(
        blank=True, null=True, default=None, help_text="Link of a third party payment method"
    )
    lang = models.CharField(
        max_length=5,
        validators=[validate_language_code],
        help_text="ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US",
    )
    included_country_codes = models.CharField(
        max_length=255,
        null=False,
        blank=True,
        default="",
        help_text="A list of country codes that represent countries that can use this payment method, comma separated",
    )


class ProofOfPayment(models.Model):
    """Represents a payment made by a user."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        DONE = "DONE", "Done"

    provided_payment_details = models.TextField(
        default="", blank=True, help_text="These details are provided by the user as proof of payment"
    )
    confirmation_image_url = models.URLField(
        null=True, blank=True, default=None, help_text="URL of the confirmation image for the payment"
    )
    reference = models.CharField(
        max_length=32, null=True, default=None, blank=True, help_text="Reference for the payment"
    )
    status = models.CharField(
        max_length=8, choices=Status, default=Status.PENDING, help_text="Bag status", db_index=True
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, help_text="User who provided these details")

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self) -> None:
        if self.status == self.Status.PENDING and self.confirmation_image_url:
            raise forms.ValidationError("Confirmation image URL mustn't be provided when status is PENDING")

        if self.status == self.Status.DONE and (not self.confirmation_image_url and not self.reference):
            raise forms.ValidationError("Either confirmation_image_url or reference must be provided")

        if self.provided_payment_details is None:
            self.provided_payment_details = ""

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Invoice(models.Model):
    """Represents a payment made by a user."""

    class Status(models.TextChoices):
        FULFILLED = "FULFILLED", "Fulfilled"
        REJECTED = "REJECTED", "Rejected"
        PENDING = "PENDING", "Pending"
        REFUNDED = "REFUNDED", "Refunded"
        DISPUTED_AS_FRAUD = "DISPUTED_AS_FRAUD", "Disputed as fraud"

    amount = models.FloatField(
        default=0, help_text="If amount is 0, transaction will not be sent to stripe or any other payment processor."
    )
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency of the invoice")
    paid_at = models.DateTimeField(help_text="Date when the invoice was paid")
    refunded_at = models.DateTimeField(
        null=True, blank=True, default=None, help_text="Date when the invoice was refunded"
    )
    status = models.CharField(
        max_length=17, choices=Status, default=Status.PENDING, db_index=True, help_text="Invoice status"
    )

    bag = models.ForeignKey("Bag", on_delete=models.CASCADE, help_text="Bag", related_name="invoices")
    externally_managed = models.BooleanField(
        default=False, help_text="If the billing is managed externally outside of the system"
    )

    proof = models.OneToOneField(
        ProofOfPayment,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Proof of payment",
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Payment method, null if it uses stripe",
    )

    # it has 27 characters right now
    stripe_id = models.CharField(max_length=32, null=True, default=None, blank=True, help_text="Stripe id")

    # it has 27 characters right now
    refund_stripe_id = models.CharField(
        max_length=32, null=True, default=None, blank=True, help_text="Stripe id for refunding"
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Customer")
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, help_text="Academy owner")

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self) -> None:
        if self.payment_method and self.externally_managed is False:
            raise forms.ValidationError("Payment method cannot be setted if the billing isn't managed externally")

        if self.payment_method and self.proof is None and self.status == self.Status.FULFILLED:
            raise forms.ValidationError(
                "Proof of payment must be provided when payment method is setted and status is FULFILLED"
            )

        if self.externally_managed and self.payment_method is None:
            raise forms.ValidationError("Payment method must be setted if the billing is managed externally")

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.user.email} {self.amount} ({self.currency.code})"


class AbstractIOweYou(models.Model):
    """Common fields for all I owe you."""

    class Status(models.TextChoices):
        FREE_TRIAL = "FREE_TRIAL", "Free trial"
        ACTIVE = "ACTIVE", "Active"
        CANCELLED = "CANCELLED", "Cancelled"
        DEPRECATED = "DEPRECATED", "Deprecated"
        PAYMENT_ISSUE = "PAYMENT_ISSUE", "Payment issue"
        ERROR = "ERROR", "Error"
        FULLY_PAID = "FULLY_PAID", "Fully paid"
        EXPIRED = "EXPIRED", "Expired"

    status = models.CharField(max_length=13, choices=Status, default=Status.ACTIVE, help_text="Status", db_index=True)
    status_message = models.CharField(
        max_length=250, null=True, blank=True, default=None, help_text="Error message if status is ERROR"
    )

    invoices = models.ManyToManyField(Invoice, blank=True, help_text="Invoices")

    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Customer")
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, help_text="Academy owner")

    externally_managed = models.BooleanField(
        default=False, help_text="If the billing is managed externally outside of the system"
    )

    selected_cohort_set = models.ForeignKey(
        CohortSet,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        help_text="Cohort set which the plans and services is for",
    )
    joined_cohorts = models.ManyToManyField(Cohort, blank=True, help_text="Cohorts those that he/she joined")
    selected_mentorship_service_set = models.ForeignKey(
        MentorshipServiceSet,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        help_text="Mentorship service set which the plans and services is for",
    )
    selected_event_type_set = models.ForeignKey(
        EventTypeSet,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        help_text="Event type set which the plans and services is for",
    )

    # this reminds the plans to change the stock scheduler on change
    plans = models.ManyToManyField(Plan, blank=True, help_text="Plans to be supplied")
    conversion_info = models.JSONField(
        default=None, blank=True, null=True, help_text="UTMs and other conversion information."
    )

    country_code = models.CharField(
        max_length=2,
        null=False,
        blank=True,
        default="",
        help_text="Country code used for pricing ratio calculations",
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class PlanFinancing(AbstractIOweYou):
    """Allows to financing a plan."""

    # in this day the financing needs being paid again
    next_payment_at = models.DateTimeField(help_text="Next payment date")

    # in this moment the subscription will be expired
    valid_until = models.DateTimeField(
        help_text="Valid until, before this date each month the customer must pay, after this "
        "date the plan financing will be destroyed and if it is belonging to a cohort, the certificate will "
        "be issued after pay every installments"
    )

    # in this moment the subscription will be expired
    plan_expires_at = models.DateTimeField(
        default=None, null=True, blank=False, help_text="Plan expires at, after this date the plan will not be renewed"
    )

    # this remember the current price per month
    monthly_price = models.FloatField(
        default=0, help_text="Monthly price, we keep this to avoid we changes him/her amount"
    )
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency", null=True, blank=True)

    how_many_installments = models.IntegerField(
        default=0, help_text="How many installments to collect and build the plan financing"
    )

    def __str__(self) -> str:
        return f"{self.user.email} ({self.valid_until})"

    def clean(self) -> None:
        settings = get_user_settings(self.user.id)

        if not self.monthly_price:
            raise forms.ValidationError(
                translation(settings.lang, en="Monthly price is required", es="Precio mensual es requerido")
            )

        if not self.plan_expires_at:
            raise forms.ValidationError(
                translation(settings.lang, en="Plan expires at is required", es="Plan expires at es requerido")
            )

        if self.status == self.Status.DEPRECATED:
            raise forms.ValidationError(
                translation(
                    settings.lang,
                    en="Plan financing cannot be deprecated",
                    es="Plan financing no puede ser descontinuado",
                )
            )

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        on_create = self.pk is None

        super().save(*args, **kwargs)

        if on_create:
            signals.planfinancing_created.send_robust(instance=self, sender=self.__class__)


class Subscription(AbstractIOweYou):
    """Allows to create a subscription to a plan and services."""

    _lang = "en"

    # last time the subscription was paid
    paid_at = models.DateTimeField(help_text="Last time the subscription was paid")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency", null=True, blank=True)

    is_refundable = models.BooleanField(default=True, help_text="Is it refundable?")

    # in this day the subscription needs being paid again
    next_payment_at = models.DateTimeField(help_text="Next payment date")

    # in this moment the subscription will be expired
    valid_until = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
        db_index=True,
        help_text="Valid until, after this date the subscription will be destroyed",
    )

    # this reminds the service items to change the stock scheduler on change
    # only for consuming single items without having a plan, when you buy consumable quantities
    service_items = models.ManyToManyField(
        ServiceItem,
        blank=True,
        through="SubscriptionServiceItem",
        through_fields=("subscription", "service_item"),
        help_text="Service items to be supplied",
    )

    # remember the chosen period to pay again
    pay_every = models.IntegerField(default=1, help_text="Pay every X units (e.g. 1, 2, 3, ...)")
    pay_every_unit = models.CharField(
        max_length=10, choices=PAY_EVERY_UNIT, default=MONTH, help_text="Pay every unit (e.g. DAY, WEEK, MONTH or YEAR)"
    )

    def __str__(self) -> str:
        return f"{self.user.email} ({self.valid_until})"

    def clean(self) -> None:
        if self.status == "FULLY_PAID":
            raise forms.ValidationError(
                translation(
                    self._lang,
                    en="Subscription cannot have fully paid as status",
                    es="La suscripción no puede tener pagado como estado",
                    slug="subscription-as-fully-paid",
                )
            )

        return super().clean()

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        on_create = self.pk is None

        super().save(*args, **kwargs)

        if on_create:
            signals.subscription_created.send_robust(instance=self, sender=self.__class__)


class SubscriptionServiceItem(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, help_text="Subscription")
    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE, help_text="Service item")

    cohorts = models.ManyToManyField(Cohort, blank=True, help_text="Cohorts")
    mentorship_service_set = models.ForeignKey(
        MentorshipServiceSet, on_delete=models.CASCADE, blank=True, null=True, help_text="Mentorship service set"
    )

    def clean(self):
        if self.id and self.mentorship_service_set and self.cohorts.count():
            raise forms.ValidationError(
                translation(
                    self._lang,
                    en="You can not set cohorts and mentorship service set at the same time",
                    es="No puedes establecer cohortes y conjunto de servicios de mentoría al mismo tiempo",
                )
            )

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.service_item)


class Consumable(AbstractServiceItem):
    """This model is used to represent the units of a service that can be consumed."""

    service_item = models.ForeignKey(
        ServiceItem,
        on_delete=models.CASCADE,
        help_text="Service item, we remind the service item to know how many units was issued",
    )

    # if null, this is valid until resources are exhausted
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Customer")

    # this could be used for the queries on the consumer, to recognize which resource is belong the consumable
    cohort_set = models.ForeignKey(
        CohortSet,
        on_delete=models.CASCADE,
        default=None,
        blank=True,
        null=True,
        help_text="Cohort set which the consumable belongs to",
    )
    event_type_set = models.ForeignKey(
        EventTypeSet,
        on_delete=models.CASCADE,
        default=None,
        blank=True,
        null=True,
        help_text="Event type set which the consumable belongs to",
    )
    mentorship_service_set = models.ForeignKey(
        MentorshipServiceSet,
        on_delete=models.CASCADE,
        default=None,
        blank=True,
        null=True,
        help_text="Mentorship service set which the consumable belongs to",
    )

    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text="Valid until, this is null if the consumable is valid until resources are exhausted",
    )

    @classmethod
    def list(
        cls,
        *,
        user: User | str | int,
        lang: str = "en",
        service: Optional[Service | str | int] = None,
        service_type: Optional[str] = None,
        permission: Optional[Permission | str | int] = None,
        extra: Optional[dict] = None,
    ) -> QuerySet[Consumable]:

        if extra is None:
            extra = {}

        param = {}
        utc_now = timezone.now()

        # User
        if isinstance(user, str) and not user.isdigit():
            raise ValidationException(
                translation(
                    lang,
                    en="Client user id must be an integer",
                    es="El id del cliente debe ser un entero",
                    slug="client-user-id-must-be-an-integer",
                )
            )

        if isinstance(user, str):
            param["user__id"] = int(user)

        elif isinstance(user, int):
            param["user__id"] = user

        elif isinstance(user, User):
            param["user"] = user

        # Service
        if service and isinstance(service, str) and not service.isdigit():
            if "_" in service:
                param["service_item__service__consumer"] = service.upper()
            else:
                param["service_item__service__slug"] = service

        elif service and isinstance(service, str) and service.isdigit():
            param["service_item__service__id"] = int(service)

        elif service and isinstance(service, int):
            param["service_item__service__id"] = service

        elif isinstance(service, Service):
            param["service_item__service"] = service

        if service_type and isinstance(service_type, str):
            param["service_item__service__type"] = service_type.upper()

        # Permission
        if permission and isinstance(permission, str) and not permission.isdigit():
            param["service_item__service__groups__permissions__codename"] = permission

        elif permission and isinstance(permission, str) and permission.isdigit():
            param["service_item__service__groups__permissions__id"] = int(permission)

        elif permission and isinstance(permission, int):
            param["service_item__service__groups__permissions__id"] = permission

        elif isinstance(permission, Permission):
            param["service_item__service__groups__permissions"] = permission

        return (
            cls.objects.filter(Q(valid_until__gte=utc_now) | Q(valid_until=None), **{**param, **extra})
            .exclude(how_many=0)
            .order_by("id")
        )

    @classmethod
    @sync_to_async
    def alist(
        cls,
        *,
        user: User | str | int,
        lang: str = "en",
        service: Optional[Service | str | int] = None,
        service_type: Optional[str] = None,
        permission: Optional[Permission | str | int] = None,
        extra: dict = None,
    ) -> QuerySet[Consumable]:

        return cls.list(
            user=user, lang=lang, service=service, service_type=service_type, permission=permission, extra=extra
        )

    @classmethod
    def get(
        cls,
        *,
        user: User | str | int,
        lang: str = "en",
        service: Optional[Service | str | int] = None,
        service_type: Optional[str] = None,
        permission: Optional[Permission | str | int] = None,
        extra: Optional[dict] = None,
    ) -> Consumable | None:

        if extra is None:
            extra = {}

        return cls.list(
            user=user, lang=lang, service=service, service_type=service_type, permission=permission, extra=extra
        ).first()

    @classmethod
    @sync_to_async
    def aget(
        cls,
        *,
        user: User | str | int,
        lang: str = "en",
        service: Optional[Service | str | int] = None,
        service_type: Optional[str] = None,
        permission: Optional[Permission | str | int] = None,
        extra: Optional[dict] = None,
    ) -> Consumable | None:
        return cls.get(
            user=user, lang=lang, service=service, service_type=service_type, permission=permission, extra=extra
        )

    def clean(self) -> None:
        resources = [self.event_type_set, self.mentorship_service_set, self.cohort_set]

        how_many_resources_are_set = len([r for r in resources if r])
        settings = get_user_settings(self.user.id)

        if how_many_resources_are_set > 1:
            raise forms.ValidationError(
                translation(
                    settings.lang,
                    en="A consumable can only be associated with one resource",
                    es="Un consumible solo se puede asociar con un recurso",
                )
            )

        if self.service_item is None:
            raise forms.ValidationError(
                translation(
                    settings.lang,
                    en="A consumable must be associated with a service item",
                    es="Un consumible debe estar asociado con un artículo de un servicio",
                )
            )

        if self.how_many < 0 and self.service_item.how_many >= 0:
            self.how_many = 0

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()

        created = not self.id

        if created and self.how_many != 0:
            signals.grant_service_permissions.send_robust(instance=self, sender=self.__class__)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email}: {self.service_item.service.slug} ({self.how_many})"


class ConsumptionSession(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        DONE = "DONE", "Done"
        CANCELLED = "CANCELLED", "Cancelled"

    operation_code = models.SlugField(
        default="default", help_text="Code that identifies the operation, it could be repeated"
    )
    consumable = models.ForeignKey(Consumable, on_delete=models.CASCADE, help_text="Consumable")
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, help_text="Customer")
    eta = models.DateTimeField(help_text="Estimated time of arrival")
    duration = models.DurationField(blank=False, default=timedelta, help_text="Duration of the session")
    how_many = models.FloatField(default=0, help_text="How many units of this service can be used")
    status = models.CharField(max_length=12, choices=Status, default=Status.PENDING, help_text="Status of the session")
    was_discounted = models.BooleanField(default=False, help_text="Was it discounted")

    request = models.JSONField(
        default=dict,
        blank=True,
        help_text="Request parameters, it's used to remind and recover and consumption session",
    )

    # this should be used to get
    path = models.CharField(max_length=200, blank=True, help_text="Path of the request")
    related_id = models.IntegerField(default=None, blank=True, null=True, help_text="Related id")
    related_slug = models.CharField(
        max_length=200,
        default=None,
        blank=True,
        null=True,
        help_text="Related slug, it's human-readable identifier, it must be unique and it can only contain "
        "letters, numbers and hyphens",
    )

    def clean(self):
        self.request = self.sort_dict(self.request or {})

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    @classmethod
    def sort_dict(cls, d):
        if isinstance(d, dict):
            return {k: cls.sort_dict(v) for k, v in sorted(d.items())}

        elif isinstance(d, list):
            return [cls.sort_dict(x) for x in d]

        return d

    @classmethod
    def build_session(
        cls,
        request: WSGIRequest,
        consumable: Consumable,
        delta: timedelta,
        user: Optional[User] = None,
        operation_code: Optional[str] = None,
        force_create: bool = False,
    ) -> "ConsumptionSession":
        assert request, "You must provide a request"
        assert consumable, "You must provide a consumable"
        assert delta, "You must provide a delta"

        if operation_code is None:
            operation_code = "default"

        utc_now = timezone.now()

        resource = (
            consumable.mentorship_service_set
            or consumable.event_type_set
            or consumable.cohort_set
            or consumable.service_item.service
        )
        id = resource.id if resource else 0
        slug = resource.slug if resource else ""

        path = resource.__class__._meta.app_label + "." + resource.__class__.__name__ if resource else ""
        user = user or request.user

        if hasattr(request, "parser_context"):
            args = request.parser_context["args"]
            kwargs = request.parser_context["kwargs"]
        else:
            args = request.resolver_match.args
            kwargs = request.resolver_match.kwargs

        data = {
            "args": args,
            "kwargs": kwargs,
            "headers": {"academy": request.META.get("HTTP_ACADEMY")},
            "user": user.id,
        }

        # assert path, 'You must provide a path'
        assert delta, "You must provide a delta"

        session = None
        if force_create is False:
            session = (
                cls.objects.filter(
                    eta__gte=utc_now,
                    request=data,
                    path=path,
                    duration=delta,
                    related_id=id,
                    related_slug=slug,
                    operation_code=operation_code,
                    user=user,
                )
                .exclude(eta__lte=utc_now)
                .first()
            )

        if session:
            return session

        return cls.objects.create(
            request=data,
            consumable=consumable,
            eta=utc_now + delta,
            path=path,
            duration=delta,
            related_id=id,
            related_slug=slug,
            operation_code=operation_code,
            user=user,
        )

    @classmethod
    @sync_to_async
    def abuild_session(
        cls,
        request: WSGIRequest,
        consumable: Consumable,
        delta: timedelta,
        user: Optional[User] = None,
        operation_code: Optional[str] = None,
    ) -> "ConsumptionSession":
        return cls.build_session(request, consumable, delta, user, operation_code)

    @classmethod
    def get_session(cls, request: WSGIRequest) -> "ConsumptionSession":
        if not request.user.id:
            return None

        utc_now = timezone.now()
        if hasattr(request, "parser_context"):
            args = request.parser_context["args"]
            kwargs = request.parser_context["kwargs"]
        else:
            args = request.resolver_match.args
            kwargs = request.resolver_match.kwargs

        data = {
            "args": list(args),
            "kwargs": kwargs,
            "headers": {"academy": request.META.get("HTTP_ACADEMY")},
            "user": request.user.id,
        }

        data = cls.sort_dict(data)
        return cls.objects.filter(eta__gte=utc_now, request=data, user=request.user).first()

    @classmethod
    @sync_to_async
    def aget_session(cls, request: WSGIRequest) -> "ConsumptionSession":
        return cls.get_session(request)

    def will_consume(self, how_many: float = 1.0) -> None:
        # avoid dependency circle
        from breathecode.payments.tasks import end_the_consumption_session

        self.how_many = how_many
        self.save()

        end_the_consumption_session.apply_async(args=(self.id, how_many), eta=self.eta)

    @sync_to_async
    def awill_consume(self, how_many: float = 1.0) -> None:
        return self.will_consume(how_many)


class PlanServiceItem(models.Model):
    """M2M between plan and ServiceItem."""

    _lang = "en"

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, help_text="Plan")
    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE, help_text="Service item")


class PlanServiceItemHandler(models.Model):
    """M2M between plan and ServiceItem."""

    handler = models.ForeignKey(PlanServiceItem, on_delete=models.CASCADE, help_text="Plan service item")

    # resources associated to this service item, one is required
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, null=True, blank=True, default=None, help_text="Subscription"
    )
    plan_financing = models.ForeignKey(
        PlanFinancing, on_delete=models.CASCADE, null=True, blank=True, default=None, help_text="Plan financing"
    )

    def clean(self) -> None:
        resources = [self.subscription, self.plan_financing]
        how_many_resources_are_set = len([r for r in resources if r is not None])

        if how_many_resources_are_set == 0:
            raise forms.ValidationError("A PlanServiceItem must be associated with one resource")

        if how_many_resources_are_set != 1:
            raise forms.ValidationError("A PlanServiceItem can only be associated with one resource")

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.subscription or self.plan_financing or "Unset")


class ServiceStockScheduler(models.Model):
    """This model is used to represent the units of a service that can be consumed."""

    # all this section are M2M service items, in the first case we have a query with subscription and service
    # item for schedule the renovations
    subscription_handler = models.ForeignKey(
        SubscriptionServiceItem,
        on_delete=models.CASCADE,
        default=None,
        blank=True,
        null=True,
        help_text="Subscription service item",
    )
    plan_handler = models.ForeignKey(
        PlanServiceItemHandler,
        on_delete=models.CASCADE,
        default=None,
        blank=True,
        null=True,
        help_text="Plan service item handler",
    )

    # this reminds which scheduler generated the consumable
    consumables = models.ManyToManyField(Consumable, blank=True, help_text="Consumables")
    valid_until = models.DateTimeField(
        null=True, blank=True, default=None, help_text="Valid until, after this date the consumables will be renewed"
    )

    def clean(self) -> None:
        resources = [self.subscription_handler, self.plan_handler]
        how_many_resources_are_set = len([r for r in resources if r is not None])

        if how_many_resources_are_set == 0:
            raise forms.ValidationError("A ServiceStockScheduler must be associated with one resource")

        if how_many_resources_are_set != 1:
            raise forms.ValidationError("A ServiceStockScheduler can only be associated with one resource")

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.subscription_handler and self.subscription_handler.subscription:
            return f"{self.subscription_handler.subscription.user.email} - {self.subscription_handler.service_item}"

        if self.plan_handler and self.plan_handler.subscription:
            return f"{self.plan_handler.subscription.user.email} - {self.plan_handler.handler.service_item}"

        if self.plan_handler and self.plan_handler.plan_financing:
            return f"{self.plan_handler.plan_financing.user.email} - {self.plan_handler.handler.service_item}"

        return "Unset"


class PaymentContact(models.Model):
    """
    Represents a link between a User and their Stripe Customer ID, potentially
    scoped to a specific Academy.

    This model stores the Stripe Customer ID (`stripe_id`) associated with a
    user. If an `academy` is specified, it implies that the Stripe customer
    record is managed under that academy's Stripe account. If `academy` is
    null, it typically means the customer is managed under a default or
    central Stripe account.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payment_contacts",
        help_text="The Django User associated with this Stripe contact.",
    )
    stripe_id = models.CharField(
        max_length=255,  # Stripe IDs can be up to 255 chars, e.g., cus_xxxxxxxxxxxxxx
        help_text="The Stripe Customer ID (e.g., cus_xxxxxxxxxxxxxx). This links the user to their record in Stripe.",
    )
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        help_text=(
            "The Academy associated with this Stripe contact. If null, the contact is typically "
            "managed under a default/central Stripe account. This determines which Stripe account "
            "the customer belongs to."
        ),
    )

    def __str__(self) -> str:
        academy_name = self.academy.name if self.academy else "Default Stripe Account"
        return f"User: {self.user.email}, Stripe ID: {self.stripe_id}, Academy: {academy_name}"


GOOD = "GOOD"
BAD = "BAD"
FRAUD = "FRAUD"
UNKNOWN = "UNKNOWN"
REPUTATION_STATUS = [
    (GOOD, "Good"),
    (BAD, "BAD"),
    (FRAUD, "Fraud"),
    (UNKNOWN, "Unknown"),
]


class FinancialReputation(models.Model):
    """
    Store the reputation of a user.

    If the user has a bad reputation, the user will not be able to buy services.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="reputation", help_text="Customer")

    in_4geeks = models.CharField(max_length=17, choices=REPUTATION_STATUS, default=GOOD, help_text="4Geeks reputation")
    in_stripe = models.CharField(max_length=17, choices=REPUTATION_STATUS, default=GOOD, help_text="Stripe reputation")

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def get_reputation(self):
        """Get the worst reputation available made by an user."""

        if self.in_4geeks == FRAUD or self.in_stripe == FRAUD:
            return FRAUD

        if self.in_4geeks == BAD or self.in_stripe == BAD:
            return BAD

        if self.in_4geeks == GOOD or self.in_stripe == GOOD:
            return GOOD

        return UNKNOWN

    def __str__(self) -> str:
        return f"{self.user.email} -> {self.get_reputation()}"


class AcademyPaymentSettings(models.Model):
    """
    Store payment settings for an academy.
    """

    class POSVendor(models.TextChoices):
        STRIPE = "STRIPE", "Stripe"

    academy = models.OneToOneField(
        Academy, on_delete=models.CASCADE, related_name="payment_settings", help_text="Academy"
    )
    pos_vendor = models.CharField(
        max_length=20,
        choices=POSVendor.choices,
        default=POSVendor.STRIPE,
        help_text="Point of Sale vendor like Stripe, etc.",
    )
    pos_api_key = models.CharField(max_length=255, blank=True, help_text="API key for the POS vendor")

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self) -> str:
        return f"Payment settings for {self.academy.name}"

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
    """
    Represents a currency, adhering to ISO 4217 codes, for financial transactions.

    This model stores details about different currencies that can be used within the
    system, including their official codes, common names, and number of decimal places.
    It also allows associating currencies with countries that officially use them.

    Attributes:
        code (CharField): The 3-letter ISO 4217 currency code (e.g., USD, EUR).
                          This is unique and indexed for quick lookups.
        name (CharField): The common, human-readable name of the currency (e.g., US Dollar, Euro).
                          This is also unique.
        decimals (IntegerField): The number of decimal places typically used for this
                                 currency (e.g., 2 for USD, 0 for JPY).
        countries (ManyToManyField): A relationship to `Country` models, indicating which
                                     countries officially use this currency.
    """

    code = models.CharField(
        max_length=3, unique=True, db_index=True, help_text="ISO 4217 currency code (e.g. USD, EUR, MXN)"
    )
    name = models.CharField(max_length=20, unique=True, help_text="Currency name (e.g. US Dollar, Euro, Mexican Peso)")
    decimals = models.IntegerField(default=0, help_text="Number of decimals (e.g. 2 for USD and EUR, 0 for JPY)")

    countries = models.ManyToManyField(
        Country, blank=True, related_name="currencies", help_text="Countries that use this currency officially"
    )

    def format_price(self, value):
        """
        Formats a numerical value as a price string according to the currency's
        conventions.

        Note:
            Currently, this method defaults to using USD formatting rules provided
            by the `currencies` library, regardless of the `Currency` instance's
            actual code. This might need to be adjusted for proper internationalization.

        Args:
            value: The numerical price value to format.

        Returns:
            str: A string representation of the formatted price.
        """
        currency = CurrencyFormatter("USD")
        currency.get_money_currency()
        return currency.get_money_format(value)

    def clean(self) -> None:
        """
        Performs model-level validation before saving.

        Ensures the currency code is stored in uppercase.
        """
        self.code = self.code.upper()
        return super().clean()

    def __str__(self) -> str:
        """
        Returns a string representation of the currency.

        Returns:
            str: A string in the format "Currency Name (CODE)".
        """
        return f"{self.name} ({self.code})"


class AbstractPriceByUnit(models.Model):
    """
    An abstract base model for items that are priced per individual unit.

    This model provides common fields for defining a price for a single unit of
    an item and the currency in which that price is denominated. It's intended
    to be inherited by concrete models representing specific sellable units.

    Attributes:
        price_per_unit (FloatField): The cost for one unit of the item.
        currency (ForeignKey): A link to the `Currency` model, specifying the
                               currency of `price_per_unit`.
    """

    price_per_unit = models.FloatField(default=0, help_text="Price per unit")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency")

    def format_price(self):
        """
        Formats the `price_per_unit` (assuming `self.price` exists and holds this value)
        as a price string using the associated currency's formatting rules.

        Note:
            This method seems to expect `self.price` to exist and hold the
            `price_per_unit` value, which might not be accurate if `price_per_unit`
            is the actual field name.

        Returns:
            str: A string representation of the formatted price.
        """
        return self.currency.format_price(self.price)

    class Meta:
        abstract = True


class AbstractPriceByTime(models.Model):
    """
    An abstract base model for items priced based on recurring time periods.

    This model provides fields for defining prices for various standard time
    durations (month, quarter, half-year, year) and the currency for these
    prices. It's designed to be inherited by models representing subscriptions
    or services with time-based pricing.

    Attributes:
        price_per_month (FloatField): The price for a one-month period.
                                      Can be null or blank if not applicable.
        price_per_quarter (FloatField): The price for a three-month (quarterly) period.
                                        Can be null or blank if not applicable.
        price_per_half (FloatField): The price for a six-month (half-yearly) period.
                                     Can be null or blank if not applicable.
        price_per_year (FloatField): The price for a twelve-month (annual) period.
                                     Can be null or blank if not applicable.
        currency (ForeignKey): A link to the `Currency` model, specifying the
                               currency of the prices.
    """

    price_per_month = models.FloatField(default=None, blank=True, null=True, help_text="Price per month")
    price_per_quarter = models.FloatField(default=None, blank=True, null=True, help_text="Price per quarter")
    price_per_half = models.FloatField(default=None, blank=True, null=True, help_text="Price per half")
    price_per_year = models.FloatField(default=None, blank=True, null=True, help_text="Price per year")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency")

    def format_price(self):
        """
        Formats a price (assuming `self.price` exists and holds the relevant period's price)
        as a price string using the associated currency's formatting rules.

        Note:
            This method seems to expect `self.price` to exist and hold one of the
            period-specific prices (e.g., `price_per_month`). The logic to determine
            which price to format is not present here.

        Returns:
            str: A string representation of the formatted price.
        """
        return self.currency.format_price(self.price)

    class Meta:
        abstract = True


class AbstractAmountByTime(models.Model):
    """
    An abstract base model representing total calculated amounts for different time periods.

    This model is typically used for objects like shopping bags or invoices where the
    final amount for a chosen billing cycle (monthly, quarterly, etc.) needs to be
    stored. These amounts are usually derived from underlying priced items.

    Attributes:
        amount_per_month (FloatField): The total calculated amount for a one-month period.
        amount_per_quarter (FloatField): The total calculated amount for a three-month period.
        amount_per_half (FloatField): The total calculated amount for a six-month period.
        amount_per_year (FloatField): The total calculated amount for a twelve-month period.
        currency (ForeignKey): A link to the `Currency` model, specifying the
                               currency of these amounts.
    """

    amount_per_month = models.FloatField(default=0, help_text="Amount per month")
    amount_per_quarter = models.FloatField(default=0, help_text="Amount per quarter")
    amount_per_half = models.FloatField(default=0, help_text="Amount per half")
    amount_per_year = models.FloatField(default=0, help_text="Amount per year")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, help_text="Currency")

    def format_price(self):
        """
        Formats an amount (assuming `self.price` exists and holds the relevant period's amount)
        as a price string using the associated currency's formatting rules.

        Note:
            This method seems to expect `self.price` to exist and hold one of the
            period-specific amounts (e.g., `amount_per_month`). The logic to determine
            which amount to format is not present here.

        Returns:
            str: A string representation of the formatted price.
        """
        return self.currency.format_price(self.price)

    class Meta:
        abstract = True


# Constants for payment frequency units
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
    """
    Abstract base model for sellable assets like products, services, or plans.

    This model provides common characteristics for any item that can be offered,
    potentially with a trial period. It includes identification (slug, title),
    ownership, visibility, trial details, and an icon.

    Attributes:
        slug (CharField): A unique, human-readable identifier for the asset.
                          It's indexed and used in URLs and lookups.
        title (CharField): An optional, user-friendly title for the asset.
        owner (ForeignKey): The `Academy` that owns or offers this asset. Can be null
                            if the asset is not academy-specific.
        private (BooleanField): If True, the asset is not publicly listed or discoverable
                                by default.
        trial_duration (IntegerField): The numerical duration of a trial period (e.g., 7, 30).
        trial_duration_unit (CharField): The unit for `trial_duration` (DAY, WEEK, MONTH, YEAR).
        icon_url (URLField): An optional URL for an icon representing the asset.
        created_at (DateTimeField): Timestamp of when the asset was created.
        updated_at (DateTimeField): Timestamp of the last update to the asset.
    """

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
    """
    Represents a specific consumable service that can be offered or purchased,
    often as part of a plan or subscription.

    Services define distinct functionalities or access rights within the platform,
    such as access to cohort materials, mentorship sessions, or event participation.
    They can be associated with Django groups to grant permissions upon acquisition.

    Inherits from `AbstractAsset` for common asset properties.

    Attributes:
        groups (ManyToManyField): Django `Group` models. Users acquiring this service
                                  (typically via a `Consumable`) might be granted
                                  permissions associated with these groups.
        session_duration (DurationField): Default duration for a single session of this
                                          service, if applicable (e.g., a mentorship session).
                                          Used by `ConsumptionSession`.
        type (CharField): The type of service, chosen from `Service.Type` (e.g.,
                          COHORT_SET, MENTORSHIP_SERVICE_SET, EVENT_TYPE_SET, VOID).
                          This categorizes the service.
        consumer (CharField): Describes how the service is typically consumed or utilized,
                              chosen from `Service.Consumer` (e.g., JOIN_MENTORSHIP, EVENT_JOIN).
    """

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
        """
        Returns the slug of the service as its string representation.

        Returns:
            str: The service's slug.
        """
        return self.slug

    def save(self, *args, **kwargs):
        """
        Saves the Service instance after performing full validation.
        """
        self.full_clean()

        super().save(*args, **kwargs)


class ServiceTranslation(models.Model):
    """
    Provides internationalization for `Service` model fields.

    This model stores language-specific translations for the title and description
    of a `Service`.

    Attributes:
        service (ForeignKey): A link to the `Service` this translation belongs to.
        lang (CharField): The language code for this translation (e.g., "en-US", "es-ES").
                          Must adhere to ISO 639-1 (language) + ISO 3166-1 alpha-2 (country).
        title (CharField): The translated title of the service.
        description (CharField): The translated description of the service.
    """

    service = models.ForeignKey(Service, on_delete=models.CASCADE, help_text="Service")
    lang = models.CharField(
        max_length=5,
        validators=[validate_language_code],
        help_text="ISO 639-1 language code + ISO 3166-1 alpha-2 country code, e.g. en-US",
    )
    title = models.CharField(max_length=60, help_text="Title of the service")
    description = models.CharField(max_length=255, help_text="Description of the service")

    def __str__(self) -> str:
        """
        Returns a string representation of the service translation.

        Returns:
            str: Formatted as "language_code: Translated Title".
        """
        return f"{self.lang}: {self.title}"


UNIT = "UNIT"
SERVICE_UNITS = [
    (UNIT, "Unit"),
]


class AbstractServiceItem(models.Model):
    """
    Abstract base model for items representing a quantity of a service.

    This model defines common fields for `ServiceItem` (defining how a service is packaged)
    and `Consumable` (representing an instance of a service granted to a user).

    Attributes:
        unit_type (CharField): The type of unit for `how_many` (currently defaults to "UNIT").
                               This is indexed.
        how_many (IntegerField): The quantity of the service. A value of -1 typically
                                 indicates an unlimited quantity.
        sort_priority (IntegerField): A numerical value used for ordering these items,
                                      for example, in a user interface. Lower numbers
                                      usually indicate higher priority.
    """

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
    """
    Defines how a `Service` is packaged and offered, including quantity and renewal terms.

    A `ServiceItem` specifies a certain number of units of a particular `Service`.
    It also determines if these units are renewable and, if so, at what frequency.
    This model acts as a template for creating `Consumable` instances.

    Inherits from `AbstractServiceItem` for `unit_type`, `how_many`, and `sort_priority`.

    Attributes:
        service (ForeignKey): The `Service` that this item represents.
        is_renewable (BooleanField): If True, `Consumable` instances created from this
                                     `ServiceItem` will be renewed according to
                                     `renew_at` and `renew_at_unit`.
        renew_at (IntegerField): The numerical value for the renewal period (e.g., 1, 3).
                                 Used only if `is_renewable` is True.
        renew_at_unit (CharField): The unit for the renewal period (DAY, WEEK, MONTH, YEAR).
                                   Used only if `is_renewable` is True.
    """

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
        """
        Performs model-level validation.

        Prevents updating a `ServiceItem` instance after creation, unless it's
        within a testing environment using `mixer` (a fixture library).

        Raises:
            forms.ValidationError: If an attempt is made to update an existing `ServiceItem`
                                   outside of the allowed test context.
        """
        is_test_env = os.getenv("ENV") == "test"
        inside_mixer = hasattr(self, "__mixer__")
        if self.id and (not inside_mixer or (inside_mixer and not is_test_env)):
            raise forms.ValidationError("You cannot update a service item")

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def delete(self):
        """
        Prevents deletion of `ServiceItem` instances.

        Raises:
            forms.ValidationError: Always, to indicate that deletion is not allowed.
        """
        raise forms.ValidationError("You cannot delete a service item")

    def __str__(self) -> str:
        """
        Returns a string representation of the service item.

        Returns:
            str: Formatted as "Service Slug (Quantity)".
        """
        return f"{self.service.slug} ({self.how_many})"


class ServiceItemFeature(models.Model):
    """
    Provides language-specific descriptive features for a `ServiceItem`.

    This model stores translated titles, detailed descriptions, and concise
    one-line descriptions for a `ServiceItem`, enhancing its presentation
    in different languages.

    Attributes:
        service_item (ForeignKey): The `ServiceItem` these features describe.
        lang (CharField): The language code for this translation (e.g., "en-US", "es-ES").
        title (CharField): The translated title for the service item. Can be null.
        description (CharField): A detailed translated description of the service item.
        one_line_desc (CharField): A short, translated one-line summary of the service item.
    """

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
        """
        Returns a string representation of the service item feature.

        Returns:
            str: Formatted as "language_code Service_Slug (ServiceItem_Quantity)".
        """
        return f"{self.lang} {self.service_item.service.slug} ({self.service_item.how_many})"


class FinancingOption(models.Model):
    """
    Defines a specific financing option, typically for a `Plan`.

    This model specifies a monthly price, currency, and the number of months (installments)
    for a particular financing arrangement. It also supports `pricing_ratio_exceptions`
    for country-specific pricing adjustments.

    Attributes:
        monthly_price (FloatField): The price per month for this financing option.
        currency (ForeignKey): The `Currency` for the `monthly_price`.
        pricing_ratio_exceptions (JSONField): A dictionary for country-specific pricing
                                              overrides (direct prices or ratios).
                                              Example: `{"us": {"monthly_price": 10, "currency": "USD"}, "gb": {"ratio": 0.8}}`
        how_many_months (IntegerField): The total number of monthly installments for this option.
    """

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
        """
        Performs model-level validation.

        Ensures that `monthly_price` is provided.

        Raises:
            forms.ValidationError: If `monthly_price` is not set.
        """
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
        """
        Saves the FinancingOption instance after full validation.
        """
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        """
        Returns a string representation of the financing option.

        Returns:
            str: Formatted as "MonthlyPrice CurrencyCode per NumberOfMonths months".
        """
        return f"{self.monthly_price} {self.currency.code} per {self.how_many_months} months"


class CohortSet(models.Model):
    """
    A collection of `Cohort` instances, often used to group cohorts for a `Plan`
    or `Service`.

    `CohortSet` allows defining a bundle of cohorts that can be offered together.
    It's associated with an `Academy`.

    Attributes:
        slug (SlugField): A unique, human-readable identifier for the cohort set. Indexed.
        academy (ForeignKey): The `Academy` that owns this cohort set.
        cohorts (ManyToManyField): The `Cohort` instances included in this set, managed
                                   through the `CohortSetCohort` intermediate model.
    """

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
        """
        Saves the CohortSet instance after full validation.
        """
        self.full_clean()
        return super().save(*args, **kwargs)


class CohortSetTranslation(models.Model):
    """
    Provides language-specific translations for `CohortSet` fields.

    Stores translated titles, descriptions, and short descriptions for a `CohortSet`.

    Attributes:
        cohort_set (ForeignKey): The `CohortSet` this translation belongs to.
        lang (CharField): The language code (e.g., "en-US", "es-ES").
        title (CharField): The translated title of the cohort set.
        description (CharField): The translated detailed description.
        short_description (CharField): The translated short description.
    """

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
    """
    Intermediate model for the ManyToMany relationship between `CohortSet` and `Cohort`.

    This model enforces validation rules, such as ensuring that the `Cohort` and
    `CohortSet` belong to the same `Academy` and that the `Cohort` is available
    as SaaS (Software as a Service).

    Attributes:
        cohort_set (ForeignKey): The `CohortSet` part of the relationship.
        cohort (ForeignKey): The `Cohort` part of the relationship.
    """

    _lang = "en"

    cohort_set = models.ForeignKey(CohortSet, on_delete=models.CASCADE, help_text="Cohort set")
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, help_text="Cohort")

    def clean(self) -> None:
        """
        Performs validation for the CohortSet-Cohort relationship.

        Checks:
        - If the `cohort` is available as SaaS (either directly or via its academy).
        - If the `cohort_set` and `cohort` belong to the same academy.

        Raises:
            forms.ValidationError: If any validation check fails.
        """
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
        """
        Saves the CohortSetCohort instance after full validation.
        """
        self.full_clean()
        return super().save(*args, **kwargs)


class MentorshipServiceSet(models.Model):
    """
    A collection of `MentorshipService` instances, used to bundle mentorship services.

    Similar to `CohortSet`, this model groups mentorship services, typically for
    inclusion in `Plan`s or `Service`s. It's associated with an `Academy`.

    Attributes:
        slug (SlugField): A unique, human-readable identifier. Indexed.
        academy (ForeignKey): The `Academy` that owns this set.
        mentorship_services (ManyToManyField): The `MentorshipService` instances included.
    """

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
    """
    Provides language-specific translations for `MentorshipServiceSet` fields.

    Stores translated titles, descriptions, and short descriptions.

    Attributes:
        mentorship_service_set (ForeignKey): The `MentorshipServiceSet` being translated.
        lang (CharField): The language code.
        title (CharField): Translated title.
        description (CharField): Translated detailed description.
        short_description (CharField): Translated short description.
    """

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
    """
    A collection of `EventType` instances, used to bundle event types.

    This model groups various event types, often for offering access through `Plan`s
    or `Service`s. It's associated with an `Academy`.

    Attributes:
        slug (SlugField): A unique, human-readable identifier. Indexed.
        academy (ForeignKey): The `Academy` that owns this set.
        event_types (ManyToManyField): The `EventType` instances included in this set.
    """

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
    """
    Provides language-specific translations for `EventTypeSet` fields.

    Stores translated titles, descriptions, and short descriptions.

    Attributes:
        event_type_set (ForeignKey): The `EventTypeSet` being translated.
        lang (CharField): The language code.
        title (CharField): Translated title.
        description (CharField): Translated detailed description.
        short_description (CharField): Translated short description.
    """

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
    """
    Defines how a specific `Service` is offered and priced by an `Academy`.

    This model acts as a bridge between a generic `Service` (e.g., "Mentorship Session")
    and its concrete offering by a particular `Academy`. It specifies the pricing
    per unit, any bundling rules (bundle_size), maximum purchase limits (max_items, max_amount),
    discount ratios for bulk purchases, and any country-specific pricing exceptions
    (`pricing_ratio_exceptions`).

    It can also link to specific sets of resources that are part of this academy-specific
    service offering, such as available `MentorshipServiceSet`s, `EventTypeSet`s,
    or `CohortSet`s. This allows, for example, an academy to offer "Mentorship Pack A"
    which uses the generic "Mentorship Session" service but is tied to a specific
    set of mentors or topics defined in a `MentorshipServiceSet`.

    Attributes:
        academy (ForeignKey): The `Academy` offering this specific service configuration.
        currency (ForeignKey): The `Currency` in which `price_per_unit` and `max_amount`
                               are denominated.
        service (OneToOneField): The generic `Service` being configured by this `AcademyService`.
                                 The OneToOneField implies that an `Academy` can have only
                                 one `AcademyService` configuration per generic `Service`.
        price_per_unit (FloatField): The base price for a single unit of the service at this academy.
        bundle_size (FloatField): The minimum number of units a user must purchase at once.
                                  This can be used to offer discounts for larger bundles.
                                  For example, if `bundle_size` is 5, users buy in multiples of 5.
        max_items (FloatField): The maximum number of individual service items (not bundles)
                                that can be purchased in a single transaction or hold at a time
                                (depending on consumption logic).
        max_amount (FloatField): The maximum total monetary value that can be purchased in a
                                 single transaction or represent as a balance for this service.
        discount_ratio (FloatField): A ratio (e.g., 0.9 for a 10% discount) applied when
                                     calculating the final price, often used in conjunction
                                     with `bundle_size` for volume discounts.
        pricing_ratio_exceptions (JSONField): A dictionary to define country-specific pricing.
                                              Overrides general pricing rules for specific countries.
                                              Example: `{"us": {"price_per_unit": 10, "currency": "USD"}, "gb": {"ratio": 0.8}}`
        available_mentorship_service_sets (ManyToManyField): Specific `MentorshipServiceSet`s
                                                              associated with this academy's
                                                              offering of the service.
        available_event_type_sets (ManyToManyField): Specific `EventTypeSet`s associated.
        available_cohort_sets (ManyToManyField): Specific `CohortSet`s associated.
    """

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
        """
        Returns a string representation of the AcademyService, typically showing
        the academy name and the service title/slug.
        """
        return f"{self.academy.name} - {self.service.title or self.service.slug}"

    def validate_transaction(
        self, total_items: float, lang: Optional[str] = "en", country_code: Optional[str] = None
    ) -> None:
        """
        Validates if a requested number of items can be purchased based on bundle size,
        maximum item limits, and maximum total amount.

        Args:
            total_items: The total number of individual service items the user wants to purchase.
            lang: Language code for error messages.
            country_code: Optional country code for applying pricing ratios to `max_amount`.

        Raises:
            ValidationException:
                - If `total_items` is not a multiple of `bundle_size`.
                - If `total_items` exceeds `max_items`.
                - If the calculated total price for `total_items` exceeds `max_amount`.
        """

        # can't buy less than bundle_size
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
        """
        Calculates the maximum purchase amount allowed for this service, considering
        country-specific pricing ratios if applicable.

        It uses the `apply_pricing_ratio` utility to adjust `self.max_amount` based
        on the `country_code` and any `pricing_ratio_exceptions` defined on this
        `AcademyService` instance.

        Args:
            country_code: Optional. The two-letter ISO country code for which to
                          calculate the maximum amount. If None, or if no specific
                          ratio applies, the base `self.max_amount` is used.

        Returns:
            The maximum purchase amount, potentially adjusted for the given country.
        """
        if self._max_amount is not None:
            return self._max_amount

        return self.pricing_ratio_exceptions.get(country_code, {}).get("max_amount", self.max_amount)

    def get_discounted_price(
        self, num_items: float, country_code: Optional[str] = None, lang: Optional[str] = "en"
    ) -> tuple[float, Currency, dict]:
        """
        Calculates the price for a given number of items, applying bundle discounts
        and country-specific pricing ratios.

        The logic is:
        1. Determine the number of bundles based on `num_items` and `self.bundle_size`.
        2. Calculate the price per bundle by multiplying `self.price_per_unit` by `self.bundle_size`.
        3. Apply `self.discount_ratio` to the price per bundle.
        4. Apply country-specific pricing ratios (from `self.pricing_ratio_exceptions` or
           general settings) to the discounted price per bundle using `apply_pricing_ratio`.
        5. Multiply the final price per bundle by the number of bundles to get the total price.

        Args:
            num_items: The total number of individual service items being priced.
            country_code: Optional. The two-letter ISO country code for regional pricing.
            lang: Optional. Language code for translations in `apply_pricing_ratio`.

        Returns:
            A tuple containing:
                - The final total price for `num_items`.
                - The `Currency` object used for the final price.
                - A dictionary explaining any pricing ratios applied (`pricing_ratio_explanation`).

        Raises:
            ValidationException: If `num_items` is not a multiple of `bundle_size` (though
                                 this should ideally be caught by `validate_transaction`).
        """
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
        """
        Performs model validation before saving.

        Ensures that:
        - `price_per_unit` is not negative.
        - `bundle_size`, `max_items`, `max_amount` are positive.
        - `discount_ratio` is between 0 and 1 (inclusive).
        - If `pricing_ratio_exceptions` are defined, they are a dictionary.
        - If a currency is specified in `pricing_ratio_exceptions`, it exists.

        Raises:
            ValidationError: If any validation rule is violated.
        """
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
        """
        Overrides the default save method to ensure `clean()` is called.
        """
        self.full_clean()
        self._price = None
        self._max_amount = None
        self._currency = None
        self._pricing_ratio_explanation = None
        return super().save(*args, **kwargs)


class Plan(AbstractPriceByTime):
    """
    Represents a sellable plan, which can be a subscription or a one-time purchase
    with financing options. Plans bundle services and define pricing, duration, and trial periods.

    Plans can be renewable (creating `Subscription`s) or non-renewable (potentially creating
    `PlanFinancing`s). They have a status (Draft, Active, etc.), an optional lifetime,
    and trial settings. A plan can include multiple `ServiceItem`s (defining the core
    services) and `AcademyService` add-ons.
    It can also be linked to specific `CohortSet`s, `MentorshipServiceSet`s, or
    `EventTypeSet`s to target specific offerings.

    Inherits from `AbstractPriceByTime` for time-based pricing fields.

    Attributes:
        slug (CharField): Unique, human-readable identifier for the plan. Indexed.
        financing_options (ManyToManyField): `FinancingOption`s available for this plan if it's not renewable.
        is_renewable (BooleanField): If True, purchasing this plan creates a recurring `Subscription`.
                                     If False, it might involve `PlanFinancing` or be a one-time purchase.
        status (CharField): The current status of the plan (DRAFT, ACTIVE, UNLISTED, DELETED, DISCONTINUED).
        time_of_life (IntegerField): The duration for which the plan is valid if not renewable (e.g., 6).
                                     Null if `is_renewable` is True and it has a price, or if it's a free trial.
        time_of_life_unit (CharField): Unit for `time_of_life` (DAY, WEEK, MONTH, YEAR).
                                        Null under the same conditions as `time_of_life`.
        trial_duration (IntegerField): Duration of any free trial period offered with the plan.
        trial_duration_unit (CharField): Unit for `trial_duration`.
        service_items (ManyToManyField): `ServiceItem`s included in this plan, through `PlanServiceItem`.
        add_ons (ManyToManyField): `AcademyService` instances that can be purchased as add-ons with this plan.
        owner (ForeignKey): The `Academy` that owns or offers this plan. Can be null.
        is_onboarding (BooleanField): If True, this plan is specifically for user onboarding.
        has_waiting_list (BooleanField): If True, users might be added to a waiting list for this plan.
        pricing_ratio_exceptions (JSONField): Country-specific overrides for price or ratio.
        cohort_set (ForeignKey): An optional default `CohortSet` associated with this plan.
        mentorship_service_set (ForeignKey): An optional default `MentorshipServiceSet`.
        event_type_set (ForeignKey): An optional default `EventTypeSet`.
        invites (ManyToManyField): `UserInvite`s that grant access to this plan.
    """

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
        """
        Returns the slug of the plan as its string representation.

        Returns:
            str: The plan's slug.
        """
        return self.slug

    def clean(self) -> None:
        """
        Performs model-level validation for plan configuration.

        Ensures logical consistency between `is_renewable`, pricing fields (`price_per_month`, etc.),
        `time_of_life`/`time_of_life_unit`, and `trial_duration`.

        For example:
        - Non-renewable plans must have `time_of_life` and `time_of_life_unit`.
        - Renewable plans with a price should not have `time_of_life` set (duration is implicit).
        - Renewable plans with a free trial should not have `time_of_life` set during the trial.
        - Renewable plans without a price and without a free trial must have `time_of_life`.

        Raises:
            forms.ValidationError: If any configuration rule is violated.
        """

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
    """
    Provides language-specific translations for `Plan` fields.

    Stores translated titles and descriptions for a `Plan`.

    Attributes:
        plan (ForeignKey): The `Plan` this translation belongs to.
        lang (CharField): The language code (e.g., "en-US", "es-ES").
        title (CharField): The translated title of the plan.
        description (CharField): The translated description of the plan.
    """

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
        """
        Returns a string representation of the plan translation.

        Returns:
            str: Formatted as "language_code Translated_Plan_Title: (Plan_Slug)".
        """
        return f"{self.lang} {self.title}: ({self.plan.slug})"


class PlanOffer(models.Model):
    """
    Represents a special offer suggesting an alternative plan when a user views an `original_plan`.

    This is used, for example, when a plan is discontinued, to guide users towards a
    `suggested_plan`. It can optionally trigger a modal display and have an expiry date.

    Attributes:
        original_plan (ForeignKey): The `Plan` that, when viewed, triggers this offer.
        suggested_plan (ForeignKey): The `Plan` being offered as an alternative.
        show_modal (BooleanField): If True, this offer might be displayed in a modal to the user.
        expires_at (DateTimeField): Optional date and time when this offer ceases to be active.
    """

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
        """
        Validates the PlanOffer.

        Ensures that there is only one active (non-expired) PlanOffer for any given
        `original_plan` at a time.

        Raises:
            forms.ValidationError: If another active offer already exists for the `original_plan`.
        """
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
    """
    Provides language-specific translations for `PlanOffer` fields.

    Stores translated titles, descriptions, and short descriptions for a `PlanOffer`.

    Attributes:
        offer (ForeignKey): The `PlanOffer` this translation belongs to.
        lang (CharField): The language code.
        title (CharField): Translated title of the offer.
        description (CharField): Translated detailed description of the offer.
        short_description (CharField): Translated short description of the offer.
    """

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
    """
    Represents an entity (individual or business) that can be associated with `Coupon`s,
    potentially for tracking referrals or sales.

    Attributes:
        name (CharField): The name of the seller (company or individual).
        user (ForeignKey): Optional link to a Django `User` if the seller is a platform user.
        type (CharField): The type of seller (INDIVIDUAL or BUSINESS).
        is_active (BooleanField): Whether the seller is currently active and can be selected.
    """

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
        """
        Performs model-level validation for the Seller.

        Checks:
        - If `user` is provided, ensures it's not already registered as a seller.
        - `name` must be at least 3 characters long.
        - If `type` is BUSINESS, the `name` must be unique among business sellers.

        Raises:
            forms.ValidationError: If any validation fails.
        """
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
        """
        Returns the name of the seller.
        """
        return self.name


class Coupon(models.Model):
    """
    Represents a discount coupon that can be applied to purchases (typically `Bag`s).

    Coupons can offer various discount types (percentage off, fixed price), have referral
    rewards, be auto-applied, have usage limits, and be associated with specific `Plan`s
    or a `Seller`.

    Internal attributes:
        _how_many_offers: Stores the initial value of `how_many_offers` upon instantiation,
                         used in `clean()` to detect changes and update `offered_at`.

    Attributes:
        slug (SlugField): A unique identifier for the coupon, used for applying it.
        discount_type (CharField): The type of discount (NO_DISCOUNT, PERCENT_OFF, FIXED_PRICE, HAGGLING).
        discount_value (FloatField): The value of the discount. If `discount_type` is PERCENT_OFF,
                                     this is a ratio (0.0 to 1.0). Otherwise, it's a fixed amount.
        referral_type (CharField): The type of reward for the seller if this coupon is used (NO_REFERRAL,
                                   PERCENTAGE, FIXED_PRICE).
        referral_value (FloatField): The value of the referral reward.
        auto (BooleanField): If True, this coupon is treated as a special offer and might be applied automatically.
        how_many_offers (IntegerField): The total number of times this coupon can be used.
                                      -1 means unlimited. 0 means it cannot be used.
        seller (ForeignKey): Optional `Seller` associated with this coupon, for referral tracking.
        plans (ManyToManyField): `Plan`s to which this coupon can be applied. If empty and `referral_type`
                                 is not NO_REFERRAL, it might apply to all plans (logic dependent on usage).
        offered_at (DateTimeField): Timestamp when the coupon became available or when `how_many_offers` changed.
        expires_at (DateTimeField): Optional timestamp when the coupon ceases to be valid.
        created_at (DateTimeField): Timestamp of creation.
        updated_at (DateTimeField): Timestamp of last update.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initializes the Coupon instance.

        Stores the initial value of `how_many_offers` in `_how_many_offers` to track changes.
        """
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
        """
        Performs model-level validation for the Coupon.

        Checks:
        - `discount_value` and `referral_value` must be non-negative.
        - Consistency between `referral_type` and `referral_value` (e.g., if NO_REFERRAL, value should be 0 or None).
        - Uniqueness of `slug` among currently valid (non-expired) coupons.
        - If `auto` is True, `discount_type` cannot be NO_DISCOUNT.
        - Updates `offered_at` to `timezone.now()` if `how_many_offers` has changed or if it's a new coupon.

        Raises:
            forms.ValidationError: If any validation fails.
        """
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
        """
        Returns the slug of the coupon.
        """
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
    """
    Represents a shopping bag or a transaction in progress, holding plans, service items,
    and chosen payment period. It calculates and stores amounts for different periods.

    A `Bag` can be in various statuses (CHECKING, PAID, RENEWAL) and types (BAG, CHARGE, PREVIEW).
    It's associated with a `User` and an `Academy`. It can have `Coupon`s applied and stores
    information about payment installments, recurrence, and delivery status (whether the
    contents have been granted to the user, e.g., as a `Subscription` or `PlanFinancing`).
    It also handles country-specific pricing through `country_code` and
    `pricing_ratio_explanation`.

    Inherits from `AbstractAmountByTime` for `amount_per_month`, `amount_per_quarter`,
    `amount_per_half`, `amount_per_year`, and `currency`.

    Attributes:
        status (CharField): The current status of the bag (CHECKING, PAID, RENEWAL).
        type (CharField): The type of bag (BAG, CHARGE, PREVIEW, INVITED).
        chosen_period (CharField): The payment period selected by the user or for renewal
                                   (NO_SET, MONTH, QUARTER, HALF, YEAR).
        how_many_installments (IntegerField): If this bag leads to a `PlanFinancing`, this field
                                            stores the number of installments.
        coupons (ManyToManyField): `Coupon`s applied to this bag.
        academy (ForeignKey): The `Academy` associated with this transaction.
        user (ForeignKey): The `User` (customer) this bag belongs to.
        service_items (ManyToManyField): `ServiceItem`s added to the bag (typically add-ons).
        plans (ManyToManyField): `Plan`s included in the bag.
        is_recurrent (BooleanField): If True, this bag is intended to set up a recurrent payment
                                     (e.g., a `Subscription`).
        was_delivered (BooleanField): If True, the items in the bag (plans, services) have been
                                      provisioned to the user (e.g., `Subscription` created).
        pricing_ratio_explanation (JSONField): Stores a detailed explanation if country-specific
                                               pricing ratios were applied.
                                               Structure: `{"plans": [{"plan": "slug", "ratio": 0.8}],
                                                           "service_items": [{"service": "slug", "ratio": 0.9}]}`
        token (CharField): An optional unique token, often used for preview bags to allow access
                           via a URL before payment.
        expires_at (DateTimeField): Optional expiration date and time for the bag, especially for
                                    preview bags with a token.
        country_code (CharField): Two-letter ISO country code of the user, used for applying
                                  country-specific pricing ratios.
        currency (ForeignKey): The final `Currency` of the bag after considering all items and
                               potential pricing ratio overrides. Can be null initially.
        created_at (DateTimeField): Timestamp of creation.
        updated_at (DateTimeField): Timestamp of last update.
    """

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
        """
        Saves the Bag instance.

        If the bag is being created, it triggers an activity log entry
        (`bag_created`) for the associated user.
        Performs full cleaning before saving.
        """
        created = self.pk is None
        self.full_clean()
        super().save(*args, **kwargs)

        if created:
            tasks_activity.add_activity.delay(
                self.user.id, "bag_created", related_type="payments.Bag", related_id=self.id
            )

    def __str__(self) -> str:
        """
        Returns a string representation of the Bag.

        Returns:
            str: Formatted as "BagType BagStatus ChosenPeriod".
        """
        return f"{self.type} {self.status} {self.chosen_period}"


class PaymentMethod(models.Model):
    """
    Represents different payment methods available at an academy, often for manual/
    externally managed payments.

    This model allows academies to define various ways users can pay, such as
    bank transfer, third-party links, or even indicating if it's a credit card
    payment (though no card details are stored here).

    Attributes:
        academy (ForeignKey): The `Academy` offering this payment method. Can be null
                              if it's a generic method.
        title (CharField): A descriptive title for the payment method (e.g., "Bank Transfer", "PayPal").
        currency (ForeignKey): The `Currency` accepted by this payment method. Can be null.
        is_credit_card (BooleanField): True if this method represents a credit card payment
                                     (for informational purposes, no card data is stored).
        description (CharField): A more detailed description of the payment method, potentially
                                 including instructions.
        third_party_link (URLField): An optional URL to an external payment gateway or page
                                     if this method involves a third party.
        lang (CharField): Language code for the title and description, for localization.
        included_country_codes (CharField): A comma-separated list of ISO country codes where
                                            this payment method is available. If empty, it's
                                            assumed to be globally available within the academy.
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
    """
    Represents evidence provided by a user or staff for a payment made, typically for
    manual or externally processed transactions.

    This model stores details about a payment claim, which can include textual details,
    a reference number, or an uploaded confirmation image. It's used to track and verify
    payments that don't go through an automated online gateway integrated with the system.

    Attributes:
        provided_payment_details (TextField): Textual information supplied by the user or staff
                                            as part of the proof (e.g., transaction ID, notes).
        confirmation_image_url (URLField): An optional URL to an image file (e.g., a screenshot
                                           of a bank transfer confirmation) stored externally.
                                           This is set after the file is successfully transferred.
        reference (CharField): An optional reference number for the payment (e.g., bank reference).
        status (CharField): The status of the proof (PENDING, DONE).
                            PENDING: Awaiting image transfer or verification.
                            DONE: Image transferred (if any) and/or reference noted.
        created_by (ForeignKey): The Django `User` (staff or customer) who submitted this proof.
        created_at (DateTimeField): Timestamp of creation.
        updated_at (DateTimeField): Timestamp of last update.
    """

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
        """
        Performs model-level validation for the ProofOfPayment.

        Checks:
        - If `status` is PENDING, `confirmation_image_url` must not be set (it's set by a task later).
        - If `status` is DONE, either `confirmation_image_url` or `reference` must be provided.
        - Ensures `provided_payment_details` is an empty string if None (for database consistency).

        Raises:
            forms.ValidationError: If any validation fails.
        """
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
    """
    Represents a financial invoice for a transaction, detailing the amount, currency,
    payment status, and associated items (via `Bag`).

    An invoice is generated for each payment attempt or completed payment. It links to
    the `User` (customer), `Academy`, `Bag` (which contains the items being paid for),
    and potentially a `ProofOfPayment` and `PaymentMethod` if externally managed.
    For payments processed via Stripe, it stores the `stripe_id`.

    Attributes:
        amount (FloatField): The total amount of the invoice. If 0, it typically represents
                             a free item or trial, and no payment processing is attempted.
        currency (ForeignKey): The `Currency` of the invoice amount.
        paid_at (DateTimeField): Timestamp when the invoice was successfully paid.
        refunded_at (DateTimeField): Optional timestamp if the invoice was refunded.
        status (CharField): The current status of the invoice (FULFILLED, REJECTED, PENDING, REFUNDED, DISPUTED_AS_FRAUD).
        bag (ForeignKey): The `Bag` associated with this invoice, detailing what was purchased.
        externally_managed (BooleanField): If True, this invoice payment was handled outside
                                          the system's automated payment gateways (e.g., manual bank transfer).
        proof (OneToOneField): Optional link to a `ProofOfPayment` if `externally_managed` is True.
        payment_method (ForeignKey): Optional link to a `PaymentMethod` if `externally_managed` is True.
        stripe_id (CharField): The Stripe PaymentIntent ID or Charge ID if paid via Stripe.
        refund_stripe_id (CharField): The Stripe Refund ID if refunded via Stripe.
        user (ForeignKey): The `User` (customer) this invoice is for.
        academy (ForeignKey): The `Academy` associated with this invoice.
        created_at (DateTimeField): Timestamp of creation.
        updated_at (DateTimeField): Timestamp of last update.
    """

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
        """
        Performs model-level validation for the Invoice.

        Checks:
        - If `payment_method` is set, `externally_managed` must be True.
        - If `payment_method` is set and `status` is FULFILLED, `proof` must be provided.
        - If `externally_managed` is True, `payment_method` must be set.

        Raises:
            forms.ValidationError: If any validation fails.
        """
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
        """
        Returns a string representation of the Invoice.

        Returns:
            str: Formatted as "UserEmail Amount (CurrencyCode)".
        """
        return f"{self.user.email} {self.amount} ({self.currency.code})"


class AbstractIOweYou(models.Model):
    """
    Abstract base model for entities representing an ongoing service obligation
    from the platform to a user, such as a subscription or a financing plan.

    This model provides common fields for tracking the status of the obligation,
    associated invoices, user, academy, linked resources (cohort sets, etc.),
    and conversion information.

    Attributes:
        status (CharField): The current status of the obligation (e.g., ACTIVE, CANCELLED,
                            PAYMENT_ISSUE, EXPIRED). Chosen from `AbstractIOweYou.Status`.
        status_message (CharField): An optional message providing more details if the status
                                    is ERROR or PAYMENT_ISSUE.
        invoices (ManyToManyField): `Invoice`s related to this obligation (payments made).
        user (ForeignKey): The `User` (customer) to whom the service is owed.
        academy (ForeignKey): The `Academy` providing the service.
        externally_managed (BooleanField): If True, billing for this obligation is handled
                                          outside the system's automated gateways.
        selected_cohort_set (ForeignKey): Optional `CohortSet` the user has access to via this obligation.
        joined_cohorts (ManyToManyField): `Cohort`s the user has actively joined through this obligation.
        selected_mentorship_service_set (ForeignKey): Optional `MentorshipServiceSet` available.
        selected_event_type_set (ForeignKey): Optional `EventTypeSet` available.
        plans (ManyToManyField): `Plan`s included in this obligation. This is important for
                                 tracking which `ServiceStockScheduler`s need updates if a plan changes.
        conversion_info (JSONField): UTM parameters and other marketing conversion data captured
                                     at the time of signup/purchase.
        country_code (CharField): Two-letter ISO country code of the user, for pricing/regionalization.
        created_at (DateTimeField): Timestamp of creation.
        updated_at (DateTimeField): Timestamp of last update.
    """

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

    coupons = models.ManyToManyField(
        Coupon, blank=True, help_text="Coupons applied during the sale", limit_choices_to=limit_coupon_choices
    )

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
    """
    Represents a financing arrangement for a plan, where a user pays in installments.

    This model tracks the details of a financed plan, including the next payment date,
    when the financing term ends (`valid_until`), when the underlying plan access expires
    (`plan_expires_at`), the monthly price, and the total number of installments.

    Inherits from `AbstractIOweYou` for common obligation-tracking fields.

    Attributes:
        next_payment_at (DateTimeField): The date and time when the next installment payment is due.
        valid_until (DateTimeField): The date and time when the financing period ends. After this date,
                                     all installments should have been paid. For cohort-based plans,
                                     a certificate might be issued after this point if all payments are made.
        plan_expires_at (DateTimeField): The date and time when access to the services granted by the
                                         associated plan(s) will expire, regardless of financing status.
        monthly_price (FloatField): The fixed monthly installment amount. Stored to avoid changes if base plan prices alter.
        currency (ForeignKey): The `Currency` of the `monthly_price`.
        how_many_installments (IntegerField): The total number of installments for this financing plan.
    """

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
    """
    Represents a user's subscription to one or more plans, typically involving recurring payments.

    This model tracks the subscription's lifecycle, including payment dates, validity period,
    associated service items, and payment frequency. It can also handle free trials or
    perpetually free subscriptions.

    Inherits from `AbstractIOweYou` for common obligation-tracking fields.

    Attributes:
        paid_at (DateTimeField): Timestamp of the last successful payment for this subscription.
        currency (ForeignKey): The `Currency` of the subscription payments.
        is_refundable (BooleanField): Indicates if payments for this subscription are generally refundable.
        next_payment_at (DateTimeField): The date and time when the next recurring payment is due.
        valid_until (DateTimeField): Optional date and time when the subscription will naturally expire
                                     (e.g., for fixed-term subscriptions or after a trial). If None,
                                     it might be a perpetually active subscription until cancelled.
                                     Indexed for performance.
        service_items (ManyToManyField): `ServiceItem`s granted directly by this subscription (not via a Plan),
                                         managed through `SubscriptionServiceItem`.
                                         Used for buying consumable quantities directly.
        pay_every (IntegerField): The numerical frequency of payments (e.g., 1, 3).
        pay_every_unit (CharField): The unit for `pay_every` (DAY, WEEK, MONTH, YEAR).
    """

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
    """
    Intermediate model for the ManyToMany relationship between `Subscription` and `ServiceItem`.

    This allows `ServiceItem`s to be directly associated with a `Subscription` independent of a `Plan`.
    It can also link these service items to specific `Cohort`s or a `MentorshipServiceSet` if the
    service grants access to such resources.

    Attributes:
        subscription (ForeignKey): The `Subscription` part of the relationship.
        service_item (ForeignKey): The `ServiceItem` being granted by the subscription.
        cohorts (ManyToManyField): Optional `Cohort`s the user gains access to via this specific
                                   service item within this subscription.
        mentorship_service_set (ForeignKey): Optional `MentorshipServiceSet` the user gains access to.
    """

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
    """
    Represents a specific instance of a service item granted to a user, forming their "stock"
    of that service. For example, if a user buys 5 mentorship sessions, they would have
    one or more `Consumable` instances totaling 5 units.

    `Consumable`s are linked to a `ServiceItem` (which defines the type of service and
    its properties like renewability) and a `User`. They specify `how_many` units the user
    possesses for this instance and until when (`valid_until`) they can be used.

    They can also be tied to specific resources like a `CohortSet`, `EventTypeSet`, or
    `MentorshipServiceSet` if the service grant is restricted to those. For example,
    "5 mentorship sessions for Cohort X".

    Inherits from `AbstractServiceItem` for `unit_type`, `how_many` (representing the
    quantity in this specific grant), and `sort_priority`.

    Static methods like `list()` and `get()` provide convenient ways to query a user's
    consumables based on various criteria.

    Attributes:
        service_item (ForeignKey): The `ServiceItem` template from which this consumable
                                   instance was created or is based. This link provides
                                   details about the nature of the service.
        user (ForeignKey): The `User` who owns this stock of consumables.
        cohort_set (ForeignKey): Optional. If this consumable grant is specific to a
                                 `CohortSet`, this field links to it.
        event_type_set (ForeignKey): Optional. If specific to an `EventTypeSet`.
        mentorship_service_set (ForeignKey): Optional. If specific to a `MentorshipServiceSet`.
        valid_until (DateTimeField): The date and time when this specific grant of
                                     consumables expires. Can be null for non-expiring
                                     consumables or those whose expiry is managed differently.
                                     Indexed for performance.
        created_at (DateTimeField): Timestamp of creation.
        updated_at (DateTimeField): Timestamp of last update.
    """

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


class ConsumptionSession(models.Model):
    """
    Tracks an instance of a user consuming a service, acting as a reservation or a record
    of use. For example, when a user books a mentorship session, a `ConsumptionSession`
    is created.

    It links a `Consumable` (the user's stock) to a specific consumption event.
    Key attributes include the `status` (PENDING, DONE, CANCELLED), the estimated time
    of arrival (`eta`) for the consumption, the `duration`, and `how_many` units
    are being consumed in this session.

    The `request` and `path` fields can store details about the HTTP request that initiated
    the consumption, allowing for session recovery or auditing. `related_id` and
    `related_slug` can link to other relevant models (e.g., the ID of a `MentorshipSession`
    or an `Event`).

    Static methods `build_session` and `get_session` provide helpers for creating
    and retrieving sessions based on request data. The `will_consume` method
    is used to mark the session as 'DONE' and trigger the actual deduction of
    consumable units.

    Attributes:
        operation_code (SlugField): A code to identify the type of operation that
                                    triggered this consumption (e.g., "mentorship-booking",
                                    "event-check-in"). Defaults to "default".
        consumable (ForeignKey): The `Consumable` instance from which units are being consumed.
        user (ForeignKey): The `User` consuming the service.
        eta (DateTimeField): Estimated Time of Arrival/start for the consumption event.
        duration (DurationField): The duration of this consumption session.
        how_many (FloatField): The number of units of the `Consumable` being used in this session.
        status (CharField): The current status of the session (PENDING, DONE, CANCELLED).
        was_discounted (BooleanField): True if the `Consumable` units for this session have
                                       been successfully deducted.
        request (JSONField): Stores the request parameters (e.g., GET/POST data) that
                             initiated this session, useful for recovery or context.
        path (CharField): The request path (URL) that initiated this session.
        related_id (IntegerField): Optional ID of a related model (e.g., `MentorshipSession.id`).
        related_slug (CharField): Optional slug of a related model.
        created_at (DateTimeField): Timestamp of creation.
        updated_at (DateTimeField): Timestamp of last update.
    """

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
    """
    Intermediate model for the ManyToMany relationship between `Plan` and `ServiceItem`.

    This model defines how a `ServiceItem` is included within a `Plan`. It specifies the
    quantity (`how_many`) of the service item granted by the plan and can optionally link
    it to a `CohortSet`, `MentorshipServiceSet`, or `EventTypeSet` if the service item's
    provisioning is tied to one of these specific resource set types within the context of the plan.

    Attributes:
        plan (ForeignKey): The `Plan` this item belongs to.
        service_item (ForeignKey): The `ServiceItem` being included in the plan.
        how_many (FloatField): The quantity of this service item provided by the plan.
        cohort_set (ForeignKey): Optional `CohortSet` this service item is specifically for
                                 within this plan.
        mentorship_service_set (ForeignKey): Optional `MentorshipServiceSet` for this item in this plan.
        event_type_set (ForeignKey): Optional `EventTypeSet` for this item in this plan.
    """

    _lang = "en"

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, help_text="Plan")
    service_item = models.ForeignKey(ServiceItem, on_delete=models.CASCADE, help_text="Service item")


class PlanServiceItemHandler(models.Model):
    """
    Acts as an intermediary linking a `PlanServiceItem` to a specific active financial
    agreement, which can be either a `Subscription` or a `PlanFinancing`.

    When a user acquires a plan (either through a subscription or a financing arrangement),
    this model creates instances that signify: "this user, via this specific subscription
    (or plan financing), has access to this particular service item as defined in the plan."

    This linkage is crucial for the `ServiceStockScheduler`. The scheduler needs to
    know which `Subscription` or `PlanFinancing` is the source of the service item grant
    to correctly manage its renewal cycle and validity period, tying it directly to
    that financial agreement.

    A `PlanServiceItemHandler` instance must be associated with *either* a `Subscription`
    *or* a `PlanFinancing`, but never both, to maintain a clear line of service provision.

    Attributes:
        handler (ForeignKey): The `PlanServiceItem` that defines the service item itself
                              and its inclusion in a `Plan`. This specifies *what* service
                              item is being granted.
        subscription (ForeignKey): Optional. The `Subscription` through which the user
                                   is receiving this plan service item. This field is null
                                   if the service item is granted via a `PlanFinancing`.
        plan_financing (ForeignKey): Optional. The `PlanFinancing` through which the user
                                     is receiving this plan service item. This field is null
                                     if the service item is granted via a `Subscription`.
    """

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
        """
        Returns a string representation of the PlanServiceItemHandler.

        The representation aims to clearly identify the link, showing whether it's
        tied to a Subscription or PlanFinancing, and referencing the handler ID.
        Example: "PlanServiceItemHandler 1 (Subscription: 5)" or
                 "PlanServiceItemHandler 1 (PlanFinancing: 3)".
        """
        if self.subscription:
            return f"PlanServiceItemHandler {self.id} (Subscription: {self.subscription.id})"
        if self.plan_financing:
            return f"PlanServiceItemHandler {self.id} (PlanFinancing: {self.plan_financing.id})"
        return f"PlanServiceItemHandler {self.id} (Unlinked)"


class ServiceStockScheduler(models.Model):
    """
    Manages the stock and validity of a `Consumable` for a `PlanFinancing` or `Subscription`.

    This model is crucial for tracking how many units of a consumable a user has, when they
    were granted, and when they expire. It links a `Consumable` to either a `PlanFinancing`
    or a `Subscription` (but not both) and specifies the `valid_from` and `valid_until` dates
    for the granted stock. It also tracks `renewed_at` for recurring grants.

    A `ServiceStockScheduler` is typically created when a user subscribes to a plan that
    includes consumables or when a financing plan starts. The `renew_consumables` task often
    manages the lifecycle and renewal of these schedulers based on the associated subscription
    or financing plan terms.

    Attributes:
        plan_financing (ForeignKey): Optional `PlanFinancing` this consumable stock is linked to.
        subscription (ForeignKey): Optional `Subscription` this consumable stock is linked to.
        consumables (ManyToManyField): The `Consumable`s whose stock is being managed by this scheduler.
                                       Typically, this would be a single consumable, but ManyToMany
                                       allows flexibility if needed, though current logic might assume one.
        valid_from (DateTimeField): The date and time from which this stock of consumables is valid.
        valid_until (DateTimeField): The date and time until which this stock of consumables is valid. Indexed.
        renewed_at (DateTimeField): Optional timestamp indicating the last time this stock was renewed
                                    or replenished. Can be null for initial grants.
        last_renew_method (CharField): The method used for the last renewal (e.g., from task, manual).
                                      Chosen from `ServiceStockScheduler.LastRenewMethod`.
    """

    class LastRenewMethod(models.TextChoices):
        TASK = "TASK", "Task"
        MANUAL = "MANUAL", "Manual"

    plan_financing = models.ForeignKey(
        PlanFinancing, on_delete=models.CASCADE, help_text="Plan financing", null=True, blank=True
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, help_text="Subscription", null=True, blank=True
    )
    consumables = models.ManyToManyField(Consumable, blank=True, help_text="Consumables")
    valid_from = models.DateTimeField(help_text="Valid from", null=True, blank=True)
    valid_until = models.DateTimeField(help_text="Valid until", db_index=True, null=True, blank=True)
    renewed_at = models.DateTimeField(help_text="Last renewed at", null=True, blank=True)
    last_renew_method = models.CharField(
        max_length=10, choices=LastRenewMethod.choices, default=LastRenewMethod.TASK, help_text="Last renew method"
    )

    def clean(self):
        """
        Performs model-level validation for ServiceStockScheduler.

        Ensures:
        - Either `plan_financing` or `subscription` is set, but not both.
        - `valid_from` is earlier than `valid_until`.
        - If `plan_financing` is set, `consumables` must be provided (at least one).

        Raises:
            forms.ValidationError: If any validation fails.
        """
        if self.plan_financing and self.subscription:
            raise forms.ValidationError("Only one of plan_financing or subscription can be set")

        if self.valid_from >= self.valid_until:
            raise forms.ValidationError("valid_from must be earlier than valid_until")

        if self.plan_financing and not self.consumables.exists():
            raise forms.ValidationError("At least one consumable must be provided if plan_financing is set")

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.plan_financing and self.plan_financing.user:
            return f"{self.plan_financing.user.email} - {self.consumables.first()}"
        if self.subscription and self.subscription.user:
            return f"{self.subscription.user.email} - {self.consumables.first()}"
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
    Stores and evaluates the financial reputation of a user based on internal
    assessments (e.g., payment history within 4Geeks) and external data
    (e.g., from Stripe).

    A user's financial reputation can influence their ability to access certain
    services or payment methods. For instance, a 'FRAUD' or 'BAD' reputation
    might lead to restrictions. The `get_reputation` method provides a consolidated
    view of the user's standing by taking the more severe status if internal and
    external reputations differ.

    Attributes:
        user (OneToOneField): The `User` whose financial reputation is being tracked.
                              The OneToOneField ensures each user has at most one
                              FinancialReputation record.
        in_4geeks (CharField): The user's reputation status as determined by internal
                               4Geeks systems. Values are from `REPUTATION_STATUS`
                               (GOOD, BAD, FRAUD, UNKNOWN).
        in_stripe (CharField): The user's reputation status as indicated by Stripe,
                               potentially based on dispute history or risk assessments.
                               Values are from `REPUTATION_STATUS`.
        created_at (DateTimeField): Timestamp indicating when the reputation record was created.
        updated_at (DateTimeField): Timestamp of the last update to the reputation record.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="reputation", help_text="Customer")

    in_4geeks = models.CharField(max_length=17, choices=REPUTATION_STATUS, default=GOOD, help_text="4Geeks reputation")
    in_stripe = models.CharField(max_length=17, choices=REPUTATION_STATUS, default=GOOD, help_text="Stripe reputation")

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def get_reputation(self):
        """
        Determines the overall financial reputation of the user by comparing
        internal (`in_4geeks`) and Stripe-based (`in_stripe`) assessments.

        It returns the more severe status if they differ. The hierarchy of severity is:
        FRAUD (most severe) > BAD > GOOD > UNKNOWN (least severe or default).

        Returns:
            str: The user's consolidated financial reputation status (GOOD, BAD, FRAUD, or UNKNOWN).
        """

        if self.in_4geeks == FRAUD or self.in_stripe == FRAUD:
            return FRAUD

        if self.in_4geeks == BAD or self.in_stripe == BAD:
            return BAD

        if self.in_4geeks == GOOD or self.in_stripe == GOOD:
            return GOOD

        return UNKNOWN

    def __str__(self) -> str:
        """
        Returns a string representation of the FinancialReputation, displaying
        the user's email and their determined overall reputation status.
        Example: "user@example.com -> GOOD".
        """
        return f"{self.user.email} -> {self.get_reputation()}"


class AcademyPaymentSettings(models.Model):
    """
    Configures and stores payment-related settings specifically for an `Academy`.

    This model enables each academy to define its preferred Point of Sale (POS)
    vendor (e.g., Stripe) and to store the necessary API keys or other credentials
    required to integrate with that vendor. This allows the system to process
    payments or manage payment-related operations correctly on behalf of the academy,
    using its designated payment gateway.

    Attributes:
        academy (OneToOneField): The `Academy` to which these payment settings apply.
                                 The OneToOneField ensures each academy has its own
                                 distinct set of payment settings.
        pos_vendor (CharField): The chosen Point of Sale vendor for the academy.
                                Currently, this is typically 'STRIPE', as defined in
                                `AcademyPaymentSettings.POSVendor`.
        pos_api_key (CharField): The API key associated with the selected `pos_vendor`
                                 for this academy. This key is essential for authenticating
                                 API requests to the payment gateway and should be stored
                                 securely.
        created_at (DateTimeField): Timestamp indicating when these settings were first created.
        updated_at (DateTimeField): Timestamp of the last modification to these settings.
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
        """
        Returns a string representation of the AcademyPaymentSettings,
        typically showing the academy name and the configured POS vendor.
        Example: "My Academy - STRIPE".
        """
        return f"{self.academy.name} - {self.pos_vendor}"

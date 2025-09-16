import os
import urllib.parse
import re
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Literal, Optional, Tuple, Type, TypedDict, Union

from adrf.requests import AsyncRequest
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q, QuerySet, Sum
from django.http import HttpRequest
from django.utils import timezone
from pytz import UTC
from rest_framework.request import Request

from breathecode.admissions.models import Academy, Cohort, CohortUser, Syllabus
from breathecode.authenticate.actions import get_user_settings, get_app_url
from breathecode.authenticate.models import UserInvite
from breathecode.notify import actions as notify_actions
from breathecode.authenticate.models import UserSetting
from breathecode.media.models import File
from breathecode.payments import tasks
from breathecode.utils import getLogger
from breathecode.utils.validate_conversion_info import validate_conversion_info
from settings import GENERAL_PRICING_RATIOS

from .models import (
    SERVICE_UNITS,
    AcademyService,
    Bag,
    CohortSet,
    Consumable,
    Coupon,
    Currency,
    EventTypeSet,
    FinancingOption,
    Invoice,
    MentorshipServiceSet,
    PaymentMethod,
    Plan,
    PlanFinancing,
    ProofOfPayment,
    Service,
    ServiceItem,
    Subscription,
    SubscriptionSeat,
    SubscriptionBillingTeam,
)

logger = getLogger(__name__)


def calculate_relative_delta(unit: float, unit_type: str):
    delta_args = {}
    if unit_type == "DAY":
        delta_args["days"] = unit

    elif unit_type == "WEEK":
        delta_args["weeks"] = unit

    elif unit_type == "MONTH":
        delta_args["months"] = unit

    elif unit_type == "YEAR":
        delta_args["years"] = unit

    return relativedelta(**delta_args)


# ------------------------------
# Seat logs utilities
# ------------------------------


def _append_seat_log(seat: SubscriptionSeat, action: str) -> None:
    """Append a log entry to both seat.seat_log and billing_team.seats_log."""
    utc_now = timezone.now()
    entry = {
        "email": (seat.email or "").strip().lower(),
        "user": seat.user_id,
        "action": action,
        "created_at": utc_now.isoformat(),
    }

    logs = list(seat.seat_log or [])
    logs.append(entry)
    seat.seat_log = logs
    seat.save(update_fields=["seat_log", "updated_at"])

    team = seat.billing_team
    team_logs = list(team.seats_log or [])
    team_logs.append(entry)
    team.seats_log = team_logs
    team.save(update_fields=["seats_log", "updated_at"])


class PlanFinder:
    cohort: Optional[Cohort] = None
    syllabus: Optional[Syllabus] = None

    def __init__(self, request: Request, lang: Optional[str] = None, query: Optional[Q] = None) -> None:
        self.request = request
        self.query = query

        if lang:
            self.lang = lang

        else:
            self.lang = request.META.get("HTTP_ACCEPT_LANGUAGE")

        if not self.lang and request.user.id:
            settings = get_user_settings(request.user.id)
            self.lang = settings.lang

        if not self.lang:
            self.lang = "en"

        self.academy_slug = request.GET.get("academy") or request.data.get("academy")

        if cohort := request.GET.get("cohort") or request.data.get("cohort"):
            self.cohort = self._get_instance(Cohort, cohort, self.academy_slug)

        if syllabus := request.GET.get("syllabus") or request.data.get("syllabus"):
            self.syllabus = self._get_instance(Syllabus, syllabus, self.academy_slug)

    def _get_pk(self, pk):
        if isinstance(pk, int) or pk.isnumeric():
            return int(pk)

        return 0

    def _get_instance(
        self, model: Type[Cohort | Syllabus], pk: str, academy: Optional[str] = None
    ) -> Optional[Cohort | Syllabus]:
        args = []
        kwargs = {}

        if isinstance(pk, int) or pk.isnumeric():
            kwargs["id"] = int(pk)
        else:
            kwargs["slug"] = pk

        if academy and model == Syllabus:
            args.append(Q(academy_owner__slug=academy) | Q(academy_owner__id=self._get_pk(academy)) | Q(private=False))

        elif academy and model == Cohort:
            args.append(Q(academy__slug=academy) | Q(academy__id=self._get_pk(academy)))

        resource = model.objects.filter(*args, **kwargs).first()
        if not resource:
            raise ValidationException(
                translation(
                    self.lang,
                    en=f"{model.__name__} not found",
                    es=f"{model.__name__} no encontrada",
                    slug=f"{model.__name__.lower()}-not-found",
                )
            )

        return resource

    def _cohort_handler(self, on_boarding: Optional[bool] = None, auto: bool = False):
        additional_args = {}

        if on_boarding is not None:
            additional_args["is_onboarding"] = on_boarding

        if not self.cohort.syllabus_version:
            return Plan.objects.none()

        if not additional_args and auto:
            additional_args["is_onboarding"] = not CohortUser.objects.filter(
                cohort__syllabus_version__syllabus=self.cohort.syllabus_version.syllabus
            ).exists()

        args = (self.query,) if self.query else tuple()
        plans = Plan.objects.filter(
            *args,
            cohort_set__cohorts__id=self.cohort.id,
            cohort_set__cohorts__stage__in=["INACTIVE", "PREWORK", "STARTED"],
            **additional_args,
        ).distinct()

        return plans

    def _syllabus_handler(self, on_boarding: Optional[bool] = None, auto: bool = False):
        additional_args = {}

        if on_boarding is not None:
            additional_args["is_onboarding"] = on_boarding

        if not additional_args and auto:
            additional_args["is_onboarding"] = not CohortUser.objects.filter(
                cohort__syllabus_version__syllabus=self.syllabus
            ).exists()

        args = (self.query,) if self.query else tuple()
        plans = Plan.objects.filter(
            *args,
            cohort_set__cohorts__syllabus_version__syllabus=self.syllabus,
            cohort_set__cohorts__stage__in=["INACTIVE", "PREWORK"],
            **additional_args,
        ).distinct()

        return plans

    def get_plans_belongs(self, on_boarding: Optional[bool] = None, auto: bool = False):
        if self.syllabus:
            return self._syllabus_handler(on_boarding, auto)

        if self.cohort:
            return self._cohort_handler(on_boarding, auto)

        raise NotImplementedError("Resource handler not implemented")

    def get_plans_belongs_from_request(self):
        is_onboarding = self.request.data.get("is_onboarding") or self.request.GET.get("is_onboarding")

        additional_args = {}

        if is_onboarding:
            additional_args["is_onboarding"] = is_onboarding

        if not additional_args:
            additional_args["auto"] = True

        return self.get_plans_belongs(**additional_args)


def ask_to_add_plan_and_charge_it_in_the_bag(plan: Plan, user: User, lang: str):
    """
    Ask to add plan to bag, and return if it must be charged or not.
    """
    utc_now = timezone.now()
    plan_have_free_trial = plan.trial_duration and plan.trial_duration_unit

    if plan.is_renewable:
        price = plan.price_per_month or plan.price_per_quarter or plan.price_per_half or plan.price_per_year

    else:
        price = not plan.is_renewable and plan.financing_options.exists()

    subscriptions = Subscription.objects.filter(user=user, plans=plan)

    # avoid bought a free trial for financing if this was bought before
    if not price and plan_have_free_trial and not plan.is_renewable and subscriptions.filter(valid_until__gte=utc_now):
        raise ValidationException(
            translation(
                lang,
                en="Free trial plans can't be bought again",
                es="Los planes de prueba no pueden ser comprados de nuevo",
                slug="free-trial-plan-for-financing",
            ),
            code=400,
        )

    # avoid bought a plan if it doesn't have a price yet after free trial
    if not price and subscriptions:
        raise ValidationException(
            translation(
                lang,
                en="Free trial plans can't be bought more than once",
                es="Los planes de prueba no pueden ser comprados más de una vez",
                slug="free-trial-already-bought",
            ),
            code=400,
        )

    # avoid financing plans if it was financed before
    if not plan.is_renewable and PlanFinancing.objects.filter(user=user, plans=plan):
        raise ValidationException(
            translation(
                lang,
                en="You already have or had a financing on this plan",
                es="Ya tienes o tuviste un financiamiento en este plan",
                slug="plan-already-financed",
            ),
            code=400,
        )

    # avoid to buy a plan if exists a subscription with same plan with remaining days
    if (
        price
        and plan.is_renewable
        and subscriptions.filter(
            Q(valid_until=None, next_payment_at__gte=utc_now) | Q(valid_until__gte=utc_now)
        ).exclude(status__in=["CANCELLED", "DEPRECATED", "EXPIRED"])
    ):
        raise ValidationException(
            translation(
                lang,
                en="You already have a subscription to this plan",
                es="Ya tienes una suscripción a este plan",
                slug="plan-already-bought",
            ),
            code=400,
        )

    # avoid to charge a plan if it has a free trial and was not bought before
    if not price or (plan_have_free_trial and not subscriptions.exists()):
        return False

    # charge a plan if it has a price
    return bool(price)


class BagHandler:

    def __init__(self, request: Request, bag: Bag, lang: str) -> None:
        self.request = request
        self.lang = lang
        self.bag = bag

        self.service_items = request.data.get("service_items")
        self.plans = request.data.get("plans")
        self.selected_cohort_set = request.data.get("cohort_set")
        self.selected_event_type_set = request.data.get("event_type_set")
        self.selected_mentorship_service_set = request.data.get("mentorship_service_set")
        self.country_code = request.data.get("country_code")
        # NEW: team seats for seat add-ons
        self.team_seats = request.data.get("team_seats")

        self.plans_not_found = set()
        self.service_items_not_found = set()
        self.cohort_sets_not_found = set()

    def _lookups(self, value, offset=""):
        args = ()
        kwargs = {}
        slug_key = f"{offset}slug__in"
        pk_key = f"{offset}id__in"

        values = value.split(",") if isinstance(value, str) and "," in value else [value]
        for v in values:
            if slug_key not in kwargs and (not isinstance(v, str) or not v.isnumeric()):
                kwargs[slug_key] = []

            if pk_key not in kwargs and (isinstance(v, int) or v.isnumeric()):
                kwargs[pk_key] = []

            if isinstance(v, int) or v.isnumeric():
                kwargs[pk_key].append(int(v))

            else:
                kwargs[slug_key].append(v)

        if len(kwargs) > 1:
            args = (Q(**{slug_key: kwargs[slug_key]}) | Q(**{pk_key: kwargs[pk_key]}),)
            kwargs = {}

        return args, kwargs

    def _more_than_one_generator(self, en, es):
        return translation(
            self.lang,
            en=f"You can only select one {en}",
            es=f"Solo puedes seleccionar una {es}",
            slug=f"more-than-one-{en}-selected",
        )

    def _validate_selected_resources(self):
        if (
            self.selected_cohort_set
            and not isinstance(self.selected_cohort_set, int)
            and not isinstance(self.selected_cohort_set, str)
        ):
            raise ValidationException(
                translation(self.lang, en="The cohort needs to be a id or slug", es="El cohort debe ser un id o slug"),
                slug="cohort-not-id-or-slug",
            )

        if (
            self.selected_event_type_set
            and not isinstance(self.selected_event_type_set, int)
            and not isinstance(self.selected_event_type_set, str)
        ):
            raise ValidationException(
                translation(
                    self.lang,
                    en="The event type set needs to be a id or slug",
                    es="El event type set debe ser un id o slug",
                ),
                slug="event-type-set-not-id-or-slug",
            )

        if (
            self.selected_mentorship_service_set
            and not isinstance(self.selected_mentorship_service_set, int)
            and not isinstance(self.selected_mentorship_service_set, str)
        ):
            raise ValidationException(
                translation(
                    self.lang,
                    en="The mentorship service set needs to be a id or slug",
                    es="El mentorship service set debe ser un id o slug",
                ),
                slug="mentorship-service-set-not-id-or-slug",
            )

    def _reset_bag(self):
        if "checking" in self.request.build_absolute_uri():
            self.bag.service_items.clear()
            self.bag.plans.clear()
            self.bag.token = None
            self.bag.expires_at = None

    def _validate_service_items_format(self):
        if isinstance(self.service_items, list):
            for item in self.service_items:
                if not isinstance(item, dict):
                    raise ValidationException(
                        translation(
                            self.lang,
                            en="The service item needs to be a object",
                            es="El service item debe ser un objeto",
                        ),
                        slug="service-item-not-object",
                    )

                if (
                    "how_many" not in item
                    or "service" not in item
                    or not isinstance(item["how_many"], int)
                    or not isinstance(item["service"], int)
                ):
                    raise ValidationException(
                        translation(
                            self.lang,
                            en="The service item needs to have the keys of the integer type how_many and service",
                            es="El service item debe tener las llaves de tipo entero how_many y service",
                        ),
                        slug="service-item-malformed",
                    )

    def _get_service_items_that_not_found(self):
        if isinstance(self.service_items, list):
            for service_item in self.service_items:
                kwargs = {}

                if service_item["service"] and (
                    isinstance(service_item["service"], int) or service_item["service"].isnumeric()
                ):
                    kwargs["id"] = int(service_item["service"])
                else:
                    kwargs["slug"] = service_item["service"]

                if Service.objects.filter(**kwargs).count() == 0:
                    self.service_items_not_found.add(service_item["service"])

    def _get_plans_that_not_found(self):
        if isinstance(self.plans, list):
            for plan in self.plans:
                kwargs = {}
                exclude = {}

                if plan and (isinstance(plan, int) or plan.isnumeric()):
                    kwargs["id"] = int(plan)
                else:
                    kwargs["slug"] = plan

                if self.selected_cohort_set and isinstance(self.selected_cohort_set, int):
                    kwargs["cohort_set"] = self.selected_cohort_set

                elif self.selected_cohort_set and isinstance(self.selected_cohort_set, str):
                    kwargs["cohort_set__slug"] = self.selected_cohort_set

                if Plan.objects.filter(**kwargs).exclude(**exclude).count() == 0:
                    self.plans_not_found.add(plan)

    def _report_items_not_found(self):
        if self.service_items_not_found or self.plans_not_found or self.cohort_sets_not_found:
            raise ValidationException(
                translation(
                    self.lang,
                    en=f"Items not found: services={self.service_items_not_found}, plans={self.plans_not_found}, "
                    f"cohorts={self.cohort_sets_not_found}",
                    es=f"Elementos no encontrados: servicios={self.service_items_not_found}, "
                    f"planes={self.plans_not_found}, cohortes={self.cohort_sets_not_found}",
                    slug="some-items-not-found",
                ),
                code=404,
            )

    def _add_service_items_to_bag(self):
        if isinstance(self.service_items, list):
            add_ons: dict[int, AcademyService] = {}

            for plan in self.bag.plans.all():
                for add_on in plan.add_ons.all():
                    add_ons[add_on.service.id] = add_on

            for service_item in self.service_items:

                if service_item["service"] not in add_ons:
                    self.bag.service_items.filter(service__id=service_item["service"]).delete()
                    raise ValidationException(
                        translation(
                            self.lang,
                            en=f"The service {service_item['service']} is not available for the selected plans",
                            es=f"El servicio {service_item['service']} no está disponible para los planes seleccionados",
                        ),
                        slug="service-item-not-valid",
                    )

                add_ons[service_item["service"]].validate_transaction(service_item["how_many"], lang=self.lang)

            for service_item in self.service_items:
                args, kwargs = self._lookups(service_item["service"])

                service = Service.objects.filter(*args, **kwargs).first()
                service_item, _ = ServiceItem.objects.get_or_create(service=service, how_many=service_item["how_many"])
                self.bag.service_items.add(service_item)

    def _add_plans_to_bag(self):
        if isinstance(self.plans, list):
            for plan in self.plans:
                kwargs = {}

                args, kwargs = self._lookups(plan)

                p = Plan.objects.filter(*args, **kwargs).first()

                if p and p not in self.bag.plans.filter():
                    self.bag.plans.add(p)

    def _validate_just_one_plan(self):
        how_many_plans = self.bag.plans.count()

        if how_many_plans > 1:

            raise ValidationException(self._more_than_one_generator(en="plan", es="plan"), code=400)

    # NEW: validate team seat add-ons for selected plan
    def _validate_seat_add_ons(self):
        if not self.team_seats:
            return

        # normalize
        try:
            seats = int(self.team_seats)
        except Exception:
            raise ValidationException(
                translation(
                    self.lang,
                    en="Seats must be an integer",
                    es="Los asientos deben ser un número entero",
                    slug="seats-must-be-an-integer",
                ),
                code=400,
            )

        if seats <= 0:
            return

        plan: Plan | None = self.bag.plans.first()
        if not plan:
            raise ValidationException(
                translation(
                    self.lang,
                    en="You must select a plan to add seats",
                    es="Debes seleccionar un plan para agregar asientos",
                    slug="plan-required-for-seats",
                ),
                code=400,
            )

        if not plan.seat_service_price:
            raise ValidationException(
                translation(
                    self.lang,
                    en="This plan does not support teams",
                    es="Este plan no soporta equipos",
                    slug="plan-not-support-teams",
                ),
                code=400,
            )

    # NEW: add seat add-ons as ServiceItems into the bag
    def _add_seat_add_ons(self):

        if not self.team_seats:
            return

        seats = int(self.team_seats)

        if seats <= 0:
            return

        plan: Plan | None = self.bag.plans.first()
        service_item, _ = ServiceItem.objects.get_or_create(
            service=plan.seat_service_price.service, how_many=seats, is_renewable=False
        )

        self.bag.seat_service_item = service_item

    def _ask_to_add_plan_and_charge_it_in_the_bag(self):
        for plan in self.bag.plans.all():
            ask_to_add_plan_and_charge_it_in_the_bag(plan, self.bag.user, self.lang)

    def execute(self):
        self._reset_bag()

        self._validate_selected_resources()
        self._validate_service_items_format()

        self._get_service_items_that_not_found()
        self._get_plans_that_not_found()
        self._report_items_not_found()
        self._add_plans_to_bag()
        # validate and add seat add-ons if requested
        self._validate_just_one_plan()
        self._validate_seat_add_ons()
        self._add_seat_add_ons()
        self._add_service_items_to_bag()
        self._validate_just_one_plan()

        self._ask_to_add_plan_and_charge_it_in_the_bag()

        # Save the country code if provided
        if self.country_code:
            self.bag.country_code = self.country_code

        self.bag.save()


def add_items_to_bag(request, bag: Bag, lang: str):
    return BagHandler(request, bag, lang).execute()


def get_amount(bag: Bag, currency: Currency, lang: str) -> tuple[float, float, float, float, Currency]:
    def add_currency(currency: Optional[Currency] = None):
        if not currency and main_currency:
            currencies[main_currency.code.upper()] = main_currency

        if currency and currency.code.upper() not in currencies:
            currencies[currency.code.upper()] = currency

    user = bag.user
    price_per_month = 0
    price_per_quarter = 0
    price_per_half = 0
    price_per_year = 0

    currencies = {}

    if not currency:
        currency, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US dollar", "decimals": 2})

    main_currency = currency

    # Initialize pricing ratio explanation with proper format
    pricing_ratio_explanation = {"plans": [], "service_items": []}

    for plan in bag.plans.all():
        must_it_be_charged = ask_to_add_plan_and_charge_it_in_the_bag(plan, user, lang)

        if not bag.how_many_installments and (bag.chosen_period != "NO_SET" or must_it_be_charged):
            # Get base prices
            base_price_per_month = plan.price_per_month or 0
            base_price_per_quarter = plan.price_per_quarter or 0
            base_price_per_half = plan.price_per_half or 0
            base_price_per_year = plan.price_per_year or 0

            # Apply pricing ratio if country code is available
            if bag.country_code:
                # Apply pricing ratio to each price type
                adjusted_price_per_month, ratio_per_month, c = apply_pricing_ratio(
                    base_price_per_month, bag.country_code, plan, lang=lang, price_attr="price_per_month"
                )
                adjusted_price_per_quarter, ratio_per_quarter, _ = apply_pricing_ratio(
                    base_price_per_quarter, bag.country_code, plan, lang=lang, price_attr="price_per_quarter"
                )
                adjusted_price_per_half, ratio_per_half, _ = apply_pricing_ratio(
                    base_price_per_half, bag.country_code, plan, lang=lang, price_attr="price_per_half"
                )
                adjusted_price_per_year, ratio_per_year, _ = apply_pricing_ratio(
                    base_price_per_year, bag.country_code, plan, lang=lang, price_attr="price_per_year"
                )

                add_currency(c)
                currency = c or currency

                # Calculate ratio for explanation if not direct price
                if adjusted_price_per_month != base_price_per_month and base_price_per_month > 0:
                    pricing_ratio_explanation["plans"].append({"plan": plan.slug, "ratio": ratio_per_month})

                elif adjusted_price_per_quarter != base_price_per_quarter and base_price_per_quarter > 0:
                    pricing_ratio_explanation["plans"].append({"plan": plan.slug, "ratio": ratio_per_quarter})

                elif adjusted_price_per_half != base_price_per_half and base_price_per_half > 0:
                    pricing_ratio_explanation["plans"].append({"plan": plan.slug, "ratio": ratio_per_half})

                elif adjusted_price_per_year != base_price_per_year and base_price_per_year > 0:
                    pricing_ratio_explanation["plans"].append({"plan": plan.slug, "ratio": ratio_per_year})

                # Use adjusted prices
                price_per_month += adjusted_price_per_month
                price_per_quarter += adjusted_price_per_quarter
                price_per_half += adjusted_price_per_half
                price_per_year += adjusted_price_per_year
            else:
                # No country code, use base prices
                price_per_month += base_price_per_month
                price_per_quarter += base_price_per_quarter
                price_per_half += base_price_per_half
                price_per_year += base_price_per_year

    plans = bag.plans.all()
    add_ons: dict[int, AcademyService] = {}
    for plan in plans:
        for add_on in plan.add_ons.filter(currency=currency):
            if add_on.service.id not in add_ons:
                add_ons[add_on.service.id] = add_on

    for service_item in bag.service_items.all():
        if service_item.service.id in add_ons:
            add_on = add_ons[service_item.service.id]

            try:
                add_on.validate_transaction(service_item.how_many, lang)
            except Exception as e:
                bag.service_items.filter().delete()
                bag.plans.filter().delete()
                raise e

            # Get discounted price first
            base_price, c, local_pricing_ratio_explanation = add_on.get_discounted_price(
                service_item.how_many, bag.country_code, lang
            )
            pricing_ratio_explanation["service_items"] += local_pricing_ratio_explanation["service_items"]
            add_currency(c)

            if price_per_month != 0:
                price_per_month += base_price

            if price_per_quarter != 0:
                price_per_quarter += base_price

            if price_per_half != 0:
                price_per_half += base_price

            if price_per_year != 0:
                price_per_year += base_price

    if len(currencies.keys()) > 1:
        raise ValidationException(
            translation(
                lang,
                en="Multiple currencies found, it means that the pricing ratio exceptions have a wrong configuration",
                es="Múltiples monedas encontradas, lo que significa que las excepciones de ratio de precios tienen una configuración incorrecta",
                slug="multiple-currencies-found",
            ),
            code=500,
        )

    # Save pricing ratio explanation if any ratios were applied
    if (
        pricing_ratio_explanation["plans"]
        or pricing_ratio_explanation["service_items"]
        or not bag.currency
        or bag.currency.id != currency.id
    ):
        bag.pricing_ratio_explanation = pricing_ratio_explanation
        bag.currency = currency
        bag.save()

    if bag.seat_service_item:
        academy_service = AcademyService.objects.filter(
            service=bag.seat_service_item.service, academy=bag.academy
        ).first()
        if not academy_service:
            raise ValidationException(
                translation(
                    lang,
                    en="Price are not configured for per-seat purchases",
                    es="Precio no configurado para compras por asiento",
                    slug="price-not-configured-for-per-seat-purchases",
                ),
                code=400,
            )

        if price_per_month != 0:
            price_per_month += academy_service.price_per_unit * bag.seat_service_item.how_many
        if price_per_quarter != 0:
            price_per_quarter += academy_service.price_per_unit * bag.seat_service_item.how_many
        if price_per_half != 0:
            price_per_half += academy_service.price_per_unit * bag.seat_service_item.how_many
        if price_per_year != 0:
            price_per_year += academy_service.price_per_unit * bag.seat_service_item.how_many

    return price_per_month, price_per_quarter, price_per_half, price_per_year


def get_amount_by_chosen_period(bag: Bag, chosen_period: str, lang: str) -> float:
    amount = 0
    seats_price = 0

    if bag.seat_service_item:
        academy_service = AcademyService.objects.filter(
            service=bag.seat_service_item.service, academy=bag.academy
        ).first()
        if not academy_service or academy_service.price_per_unit == 0:
            raise ValidationException(
                translation(
                    lang,
                    en="Price are not configured for per-seat purchases",
                    es="Precio no configurado para compras por asiento",
                    slug="price-not-configured-for-per-seat-purchases",
                ),
                code=400,
            )
        seats_price = academy_service.price_per_unit * bag.seat_service_item.how_many

    if chosen_period == "MONTH" and bag.amount_per_month:
        amount = bag.amount_per_month + seats_price

    elif chosen_period == "QUARTER" and bag.amount_per_quarter:
        amount = bag.amount_per_quarter + (seats_price * 3)

    elif chosen_period == "HALF" and bag.amount_per_half:
        amount = bag.amount_per_half + (seats_price * 6)

    elif chosen_period == "YEAR" and bag.amount_per_year:
        amount = bag.amount_per_year + (seats_price * 12)

    # free trial
    if not amount and (bag.amount_per_month or bag.amount_per_quarter or bag.amount_per_half or bag.amount_per_year):
        raise ValidationException(
            translation(
                lang,
                en=f"The period {chosen_period} is disabled for this bag",
                es=f"El periodo {chosen_period} está deshabilitado para esta bolsa",
                slug="period-disabled-for-bag",
            ),
            code=400,
        )

    return amount


def get_bag_from_subscription(
    subscription: Subscription, settings: Optional[UserSetting] = None, lang: Optional[str] = None
) -> Bag:
    bag = Bag()

    if not lang and not settings:
        settings = get_user_settings(subscription.user.id)
        lang = settings.lang
    elif settings:
        lang = settings.lang

    last_invoice = subscription.invoices.filter().last()
    if not last_invoice:
        raise Exception(
            translation(
                lang,
                en="Invalid subscription, this has no invoices",
                es="Suscripción invalida, esta no tiene facturas",
                slug="subscription-has-no-invoices",
            )
        )

    bag.status = "RENEWAL"
    bag.type = "CHARGE"
    bag.academy = subscription.academy
    bag.currency = subscription.currency or last_invoice.currency
    bag.user = subscription.user
    bag.is_recurrent = True
    bag.chosen_period = last_invoice.bag.chosen_period

    if bag.chosen_period == "NO_SET":
        bag.chosen_period = "MONTH"

    bag.save()

    for plan in subscription.plans.all():
        bag.plans.add(plan)

    # Include persisted subscription add-ons (SubscriptionServiceItem) in the bag so they are billed monthly
    for handler in subscription.subscriptionserviceitem_set.select_related("service_item").all():
        service_item = handler.service_item
        # Attach the same service_item reference into bag so pricing logic picks it up via plan.add_ons mapping
        bag.service_items.add(service_item)

    # Add only valid (non-expired) coupons from the subscription to the bag
    # Also exclude coupons where the user is the seller
    utc_now = timezone.now()

    subscription_coupons = subscription.coupons.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=utc_now)).exclude(
        seller__user=subscription.user
    )

    if subscription_coupons.exists():
        bag.coupons.set(subscription_coupons)

    bag.amount_per_month, bag.amount_per_quarter, bag.amount_per_half, bag.amount_per_year = get_amount(
        bag, subscription.currency or last_invoice.currency, lang
    )

    bag.save()

    return bag


def get_bag_from_plan_financing(plan_financing: PlanFinancing, settings: Optional[UserSetting] = None) -> Bag:
    bag = Bag()

    if not settings:
        settings = get_user_settings(plan_financing.user.id)

    last_invoice = plan_financing.invoices.filter().last()
    if not last_invoice:
        raise Exception(
            translation(
                settings.lang,
                en="Invalid plan financing, this has not charge",
                es="Plan financing es invalido, este no tiene cargos",
                slug="plan-financing-has-no-invoices",
            )
        )

    bag.status = "RENEWAL"
    bag.type = "CHARGE"
    bag.academy = plan_financing.academy
    bag.currency = plan_financing.currency or last_invoice.currency
    bag.user = plan_financing.user
    bag.is_recurrent = True
    bag.save()

    for plan in plan_financing.plans.all():
        bag.plans.add(plan)

    return bag


def filter_consumables(
    request: WSGIRequest,
    items: QuerySet[Consumable],
    queryset: QuerySet,
    key: str,
    custom_query_key: Optional[str] = None,
):

    if ids := request.GET.get(key):
        try:
            ids = [int(x) for x in ids.split(",")]
        except Exception:
            raise ValidationException(f"{key} param must be integer")

        query_key = custom_query_key or key
        queryset |= items.filter(**{f"{query_key}__id__in": ids})

    if slugs := request.GET.get(f"{key}_slug"):
        slugs = slugs.split(",")

        query_key = custom_query_key or key
        queryset |= items.filter(**{f"{query_key}__slug__in": slugs})

    if not ids and not slugs:
        query_key = custom_query_key or key
        queryset |= items.filter(**{f"{query_key}__isnull": False})

    queryset = queryset.distinct()
    return queryset


def filter_void_consumable_balance(request: WSGIRequest, items: QuerySet[Consumable]):
    consumables = items.filter(service_item__service__type="VOID")

    if ids := request.GET.get("service"):
        try:
            ids = [int(x) for x in ids.split(",")]
        except Exception:
            raise ValidationException("service param must be integer")

        consumables = consumables.filter(service_item__service__id__in=ids)

    if slugs := request.GET.get("service_slug"):
        slugs = slugs.split(",")

        consumables = consumables.filter(service_item__service__slug__in=slugs)

    if not consumables:
        return []

    result = {}

    for consumable in consumables:
        service = consumable.service_item.service
        if service.id not in result:
            result[service.id] = {
                "balance": {
                    "unit": 0,
                },
                "id": service.id,
                "slug": service.slug,
                "items": [],
            }

        if consumable.how_many < 0:
            result[service.id]["balance"]["unit"] = -1

        elif result[service.id]["balance"]["unit"] != -1:
            result[service.id]["balance"]["unit"] += consumable.how_many

        result[service.id]["items"].append(
            {
                "id": consumable.id,
                "how_many": consumable.how_many,
                "unit_type": consumable.unit_type,
                "valid_until": consumable.valid_until,
            }
        )

    return list(result.values())


def get_balance_by_resource(
    queryset: QuerySet[Consumable],
    key: str,
):
    result = []

    ids = {getattr(x, key).id for x in queryset}
    for id in ids:
        current = queryset.filter(**{f"{key}__id": id})

        instance = current.first()
        balance = {}
        items = []
        units = {x[0] for x in SERVICE_UNITS}
        for unit in units:
            per_unit = current.filter(unit_type=unit)
            balance[unit.lower()] = (
                -1 if per_unit.filter(how_many=-1).exists() else per_unit.aggregate(Sum("how_many"))["how_many__sum"]
            )

        for x in queryset:
            valid_until = x.valid_until
            if valid_until:
                valid_until = re.sub(r"\+00:00$", "Z", valid_until.replace(tzinfo=UTC).isoformat())

            items.append(
                {
                    "id": x.id,
                    "how_many": x.how_many,
                    "unit_type": x.unit_type,
                    "valid_until": x.valid_until,
                }
            )

        result.append(
            {
                "id": getattr(instance, key).id,
                "slug": getattr(instance, key).slug,
                "balance": balance,
                "items": items,
            }
        )
    return result


@lru_cache(maxsize=1)
def max_coupons_allowed():
    try:
        return int(os.getenv("MAX_COUPONS_ALLOWED", "1"))

    except Exception:
        return 1


def get_available_coupons(plan: Plan, coupons: Optional[list[str]] = None, user: Optional[User] = None) -> list[Coupon]:

    def get_total_spent_coupons(coupon: Coupon) -> int:
        sub_kwargs = {"invoices__bag__coupons": coupon}
        if coupon.offered_at:
            sub_kwargs["created_at__gte"] = coupon.offered_at

        if coupon.expires_at:
            sub_kwargs["created_at__lte"] = coupon.expires_at

        how_many_subscriptions = Subscription.objects.filter(**sub_kwargs).count()
        how_many_plan_financings = PlanFinancing.objects.filter(**sub_kwargs).count()
        total_spent_coupons = how_many_subscriptions + how_many_plan_financings

        return total_spent_coupons

    def manage_coupon(coupon: Coupon) -> None:
        # Prevent sellers from using their own coupons
        if user and coupon.seller and coupon.seller.user == user:
            founded_coupon_slugs.append(coupon.slug)
            return

        # Check if coupon is restricted to a specific user
        if coupon.allowed_user and (not user or coupon.allowed_user != user):
            founded_coupon_slugs.append(coupon.slug)
            return

        if coupon.slug not in founded_coupon_slugs:
            if coupon.how_many_offers == -1:
                founded_coupons.append(coupon)
                founded_coupon_slugs.append(coupon.slug)
                return

            if coupon.how_many_offers == 0:
                founded_coupon_slugs.append(coupon.slug)
                return

            total_spent_coupons = get_total_spent_coupons(coupon)
            if coupon.how_many_offers >= total_spent_coupons:
                founded_coupons.append(coupon)

            founded_coupon_slugs.append(coupon.slug)

    founded_coupons = []
    founded_coupon_slugs = []

    cou_args = (
        Q(plans=plan) | Q(plans=None),
        Q(offered_at=None) | Q(offered_at__lte=timezone.now()),
        Q(expires_at=None) | Q(expires_at__gte=timezone.now()),
    )
    cou_fields = ("id", "slug", "how_many_offers", "offered_at", "expires_at", "seller", "allowed_user")

    special_offers = (
        Coupon.objects.filter(*cou_args, auto=True)
        .exclude(Q(how_many_offers=0) | Q(discount_type=Coupon.Discount.NO_DISCOUNT))
        .select_related("seller__user", "allowed_user")
        .only(*cou_fields)
    )

    for coupon in special_offers:
        manage_coupon(coupon)

    valid_coupons = (
        Coupon.objects.filter(*cou_args, slug__in=coupons, auto=False)
        .exclude(how_many_offers=0)
        .select_related("seller__user", "allowed_user")
        .only(*cou_fields)
    )

    max = max_coupons_allowed()
    for coupon in valid_coupons[0:max]:
        manage_coupon(coupon)

    return founded_coupons


def get_discounted_price(price: float, coupons: list[Coupon]) -> float:
    percent_off_coupons = [x for x in coupons if x.discount_type == Coupon.Discount.PERCENT_OFF]
    fixed_discount_coupons = [
        x for x in coupons if x.discount_type not in [Coupon.Discount.NO_DISCOUNT, Coupon.Discount.PERCENT_OFF]
    ]

    for coupon in percent_off_coupons:
        price -= price * coupon.discount_value

    for coupon in fixed_discount_coupons:
        price -= coupon.discount_value

    if price < 0:
        price = 0

    return price


def validate_and_create_proof_of_payment(
    request: dict | WSGIRequest | AsyncRequest | HttpRequest | Request,
    staff_user: User,
    academy_id: int,
    lang: Optional[str] = None,
):
    from .tasks import set_proof_of_payment_confirmation_url

    if isinstance(request, (WSGIRequest, AsyncRequest, HttpRequest, Request)):
        data = request.data

    else:
        data = request

    if lang is None:
        settings = get_user_settings(staff_user.id)
        lang = settings.lang

    provided_payment_details = data.get("provided_payment_details")
    reference = data.get("reference")
    file_id = data.get("file")

    if not file_id and not reference:
        raise ValidationException(
            translation(
                lang,
                en="At least one of 'file' or'reference' must be provided",
                es="Debe proporcionar al menos un 'file' o'reference'",
                slug="at-least-one-of-file-or-reference-must-be-provided",
            ),
            code=400,
        )

    x = ProofOfPayment()
    x.provided_payment_details = provided_payment_details
    x.reference = reference
    x.created_by = staff_user

    if file_id and (
        file := File.objects.filter(
            Q(user__id=staff_user.id) | Q(academy__id=academy_id), id=file_id, status=File.Status.CREATED
        ).first()
    ):
        file.status = File.Status.TRANSFERRING
        file.save()

        x.status = ProofOfPayment.Status.PENDING
        x.save()

        set_proof_of_payment_confirmation_url.delay(file.id, x.id)

    elif file_id:
        raise ValidationException(
            translation(
                lang,
                en="Invalid file id",
                es="ID de archivo inválido",
                slug="invalid-file-id",
            ),
            code=400,
        )

    else:
        x.status = ProofOfPayment.Status.DONE
        x.save()

    return x


def validate_and_create_subscriptions(
    request: dict | WSGIRequest | AsyncRequest | HttpRequest | Request,
    staff_user: User,
    proof_of_payment: ProofOfPayment,
    academy_id: int,
    lang: Optional[str] = None,
):
    if isinstance(request, (WSGIRequest, AsyncRequest, HttpRequest, Request)):
        data = request.data

    else:
        data = request

    if lang is None:
        settings = get_user_settings(staff_user.id)
        lang = settings.lang

    how_many_installments = 1

    cohort = data.get("cohorts", [])
    cohort_found = []

    if cohort:
        for x in cohort:
            x = Cohort.objects.filter(slug=x).first()
            if not x:
                raise ValidationException(
                    translation(
                        lang,
                        en=f"Cohort not found: {x}",
                        es=f"Cohorte no encontrada: {x}",
                        slug="cohort-not-found",
                    ),
                    code=404,
                )
            cohort_found.append(x)

    extra = {}
    if cohort_found:
        extra["cohort_set__cohorts__slug__in"] = cohort

    plans = data.get("plans", [])
    plans = Plan.objects.filter(slug__in=plans, **extra).distinct()
    if plans.count() != 1:
        raise ValidationException(
            translation(
                lang,
                en="Exactly one plan must be provided",
                es="Debe proporcionar exactamente un plan",
                slug="exactly-one-plan-must-be-provided",
            ),
            code=400,
        )

    if "coupons" in data and not isinstance(data["coupons"], list):
        raise ValidationException(
            translation(
                lang,
                en="Coupons must be a list of strings",
                es="Cupones debe ser una lista de cadenas",
                slug="invalid-coupons",
            ),
            code=400,
        )

    if "coupons" in data and len(data["coupons"]) > (max := max_coupons_allowed()):
        raise ValidationException(
            translation(
                lang,
                en=f"Too many coupons (max {max})",
                es=f"Demasiados cupones (max {max})",
                slug="too-many-coupons",
            ),
            code=400,
        )

    plan = plans[0]

    if (option := plan.financing_options.filter(how_many_months=how_many_installments).first()) is None:
        raise ValidationException(
            translation(
                lang,
                en=f"Financing option not found for {how_many_installments} installments",
                es=f"Opción de financiamiento no encontrada para {how_many_installments} cuotas",
                slug="financing-option-not-found",
            ),
            code=404,
        )

    conversion_info = data["conversion_info"] if "conversion_info" in data else None
    validate_conversion_info(conversion_info, lang)

    academy = Academy.objects.filter(id=academy_id).first()
    if academy is None:
        raise ValidationException(
            translation(
                lang,
                en="Academy not found",
                es="Academia no encontrada",
                slug="academy-not-found",
            ),
            code=404,
        )

    user_pk = data.get("user", None)
    if user_pk is None:
        raise ValidationException(
            translation(
                lang,
                en="user must be provided",
                es="user debe ser proporcionado",
                slug="user-must-be-provided",
            ),
            code=400,
        )

    payment_method = data.get("payment_method")
    if not payment_method or (payment_method := PaymentMethod.objects.filter(id=payment_method).first()) is None:
        raise ValidationException(
            translation(
                lang,
                en="Payment method not provided",
                es="Método de pago no proporcionado",
                slug="payment-method-not-provided",
            ),
            code=400,
        )

    args = []
    kwargs = {}
    if isinstance(user_pk, int):
        kwargs["id"] = user_pk
    else:
        args.append(Q(email=user_pk) | Q(username=user_pk))

    if (user := User.objects.filter(*args, **kwargs).first()) is None:
        ValidationException(
            translation(
                lang,
                en=f"User not found: {user_pk}",
                es=f"Usuario no encontrado: {user_pk}",
                slug="user-not-found",
            ),
            code=404,
        )

    if PlanFinancing.objects.filter(plans=plan, user=user, valid_until__gt=timezone.now()).exists():
        raise ValidationException(
            translation(
                lang,
                en=f"User already has a valid subscription for this plan: {user_pk}",
                es=f"Usuario ya tiene una suscripción válida para este plan: {user_pk}",
                slug="user-already-has-valid-subscription",
            ),
            code=409,
        )

    # Get available coupons for this user (excluding their own coupons if they are a seller)
    coupons = get_available_coupons(plan, data.get("coupons", []), user=user)

    bag = Bag()
    bag.type = Bag.Type.BAG
    bag.user = user
    bag.currency = academy.main_currency
    bag.status = Bag.Status.PAID
    bag.academy = academy
    bag.is_recurrent = True

    bag.how_many_installments = how_many_installments
    original_price = option.monthly_price
    amount = get_discounted_price(original_price, coupons)

    bag.save()
    bag.plans.set(plans)

    utc_now = timezone.now()

    invoice = Invoice(
        amount=amount,
        paid_at=utc_now,
        user=user,
        bag=bag,
        academy=bag.academy,
        status="FULFILLED",
        currency=bag.academy.main_currency,
        externally_managed=True,
        proof=proof_of_payment,
        payment_method=payment_method,
    )
    invoice.save()

    # Create reward coupons for sellers if coupons were used
    if coupons and original_price > 0:
        create_seller_reward_coupons(coupons, original_price, user)

    tasks.build_plan_financing.delay(bag.id, invoice.id, conversion_info=conversion_info, cohorts=cohort)

    return invoice, coupons


class UnitBalance(TypedDict):
    unit: int


class ConsumableItem(TypedDict):
    id: int
    how_many: int
    unit_type: str
    valid_until: Optional[datetime]


class ResourceBalance(TypedDict):
    id: int
    slug: str
    balance: UnitBalance
    items: list[ConsumableItem]


class ConsumableBalance(TypedDict):
    mentorship_service_sets: ResourceBalance
    cohort_sets: list[ResourceBalance]
    event_type_sets: list[ResourceBalance]
    voids: list[ResourceBalance]


def set_virtual_balance(balance: ConsumableBalance, user: User) -> None:
    from breathecode.admissions.actions import is_no_saas_student_up_to_date_in_any_cohort
    from breathecode.payments.data import get_virtual_consumables

    if is_no_saas_student_up_to_date_in_any_cohort(user, default=False) is False:
        return

    virtuals = get_virtual_consumables()

    event_type_set_ids = [virtual["event_type_set"]["id"] for virtual in virtuals if virtual["event_type_set"]]
    cohort_set_ids = [virtual["cohort_set"]["id"] for virtual in virtuals if virtual["cohort_set"]]
    mentorship_service_set_ids = [
        virtual["mentorship_service_set"]["id"] for virtual in virtuals if virtual["mentorship_service_set"]
    ]

    available_services = [
        virtual["service_item"]["service"]["id"]
        for virtual in virtuals
        if virtual["service_item"]["service"]["type"] == Service.Type.VOID
    ]

    available_event_type_sets = EventTypeSet.objects.filter(
        academy__profileacademy__user=user, id__in=event_type_set_ids
    ).values_list("id", flat=True)

    available_cohort_sets = CohortSet.objects.filter(cohorts__cohortuser__user=user, id__in=cohort_set_ids).values_list(
        "id", flat=True
    )

    available_mentorship_service_sets = MentorshipServiceSet.objects.filter(
        academy__profileacademy__user=user, id__in=mentorship_service_set_ids
    ).values_list("id", flat=True)

    balance_mapping: dict[str, dict[int, int]] = {
        "cohort_sets": dict(
            [(v["id"], i) for (i, v) in enumerate(balance["cohort_sets"]) if v["id"] in available_cohort_sets]
        ),
        "event_type_sets": dict(
            [(v["id"], i) for (i, v) in enumerate(balance["event_type_sets"]) if v["id"] in available_event_type_sets]
        ),
        "mentorship_service_sets": dict(
            [
                (v["id"], i)
                for (i, v) in enumerate(balance["mentorship_service_sets"])
                if v["id"] in available_mentorship_service_sets
            ]
        ),
        "voids": dict([(v["id"], i) for (i, v) in enumerate(balance["voids"]) if v["id"] in available_services]),
    }

    def append(
        key: Literal["cohort_sets", "event_type_sets", "mentorship_service_sets", "voids"],
        id: int,
        slug: str,
        how_many: int,
        unit_type: str,
        valid_until: Optional[datetime] = None,
    ):

        index = balance_mapping[key].get(id)

        # index = balance[key].append(id)
        unit_type = unit_type.lower()
        if index is None:
            balance[key].append({"id": id, "slug": slug, "balance": {unit_type: 0}, "items": []})
            index = len(balance[key]) - 1
            balance_mapping[key][id] = index

        obj = balance[key][index]

        if how_many == -1:
            obj["balance"][unit_type] = how_many

        elif obj["balance"][unit_type] != -1:
            obj["balance"][unit_type] += how_many

        obj["items"].append(
            {
                "id": None,
                "how_many": how_many,
                "unit_type": unit_type.upper(),
                "valid_until": valid_until,
            }
        )

    for virtual in virtuals:
        if (
            virtual["service_item"]["service"]["type"] == Service.Type.VOID
            and virtual["service_item"]["service"]["id"] in available_services
        ):
            id = virtual["service_item"]["service"]["id"]
            slug = virtual["service_item"]["service"]["slug"]
            how_many = virtual["service_item"]["how_many"]
            unit_type = virtual["service_item"]["unit_type"]
            append("voids", id, slug, how_many, unit_type)

        if virtual["event_type_set"] and virtual["event_type_set"]["id"] in available_event_type_sets:
            id = virtual["event_type_set"]["id"]
            slug = virtual["event_type_set"]["slug"]
            how_many = virtual["service_item"]["how_many"]
            unit_type = virtual["service_item"]["unit_type"]
            append("event_type_sets", id, slug, how_many, unit_type)

        if (
            virtual["mentorship_service_set"]
            and virtual["mentorship_service_set"]["id"] in available_mentorship_service_sets
        ):
            id = virtual["mentorship_service_set"]["id"]
            slug = virtual["mentorship_service_set"]["slug"]
            how_many = virtual["service_item"]["how_many"]
            unit_type = virtual["service_item"]["unit_type"]
            append("mentorship_service_sets", id, slug, how_many, unit_type)

        if virtual["cohort_set"] and virtual["cohort_set"]["id"] in available_cohort_sets:
            id = virtual["cohort_set"]["id"]
            slug = virtual["cohort_set"]["slug"]
            how_many = virtual["service_item"]["how_many"]
            unit_type = virtual["service_item"]["unit_type"]
            append("cohort_sets", id, slug, how_many, unit_type)


def retry_pending_bag(bag: Bag):
    """
    This function retries the delivery of bags that are paid but not delivered.
    It is intended to be called periodically by a scheduler.
    """

    if bag.status != Bag.Status.PAID:
        return "not-paid"

    if bag.was_delivered:
        return "done"

    invoice: Invoice | None = bag.invoices.first()
    if invoice is None:
        return "no-invoice"

    if bag.how_many_installments > 0:
        tasks.build_plan_financing.delay(bag.id, invoice.id)

    elif invoice.amount > 0:
        tasks.build_subscription.delay(bag.id, invoice.id)

    else:
        tasks.build_free_subscription.delay(bag.id, invoice.id)

    return "scheduled"


def get_cached_currency(code: str, cache: dict[str, Currency]) -> Currency | None:
    """
    Get a currency from the cache by code.
    """
    currency = cache.get(code.upper())
    if currency is None:
        currency = Currency.objects.filter(code__iexact=code).first()
        cache[code.upper()] = currency
    return currency


def apply_pricing_ratio(
    price: float,
    country_code: Optional[str],
    obj: Optional[Union[Plan, AcademyService, FinancingOption]] = None,
    price_attr: str = "price",
    lang: Optional[str] = None,
    cache: Optional[dict[str, Currency]] = None,
) -> Tuple[float, Optional[float], Optional[Currency]]:
    """
    Apply pricing ratio to a price based on country code and object-specific overrides.

    Args:
        price (float): The original price to apply ratio to
        country_code (Optional[str]): Two-letter country code to look up ratio for
        obj (Optional[Union[Plan, AcademyService]]): Plan or AcademyService object that may have pricing overrides
        price_attr (str): Attribute name to use for price override
        lang (Optional[str]): Language to use for translations
        cache (Optional[dict[str, Currency]]): Cache of currencies

    Returns:
        Tuple[float, Optional[float], Optional[Currency]]: A tuple containing:
            - The final price after applying any ratio
            - The ratio that was applied (None if using object's direct price override)
            - The currency that was used for the price if it was overridden

    The function applies pricing ratios in the following order:
    1. If the object has a direct price override for the country, use that price and return None as ratio
    2. If the object has a ratio override for the country, apply that ratio
    3. If there is a general ratio defined for the country, apply that ratio
    4. Otherwise return the original price with None as ratio
    """

    if not price or not country_code:
        return price, None, None

    if cache is None:
        cache = {}

    country_code = country_code.lower()

    # Check for object-specific overrides first
    if obj and hasattr(obj, "pricing_ratio_exceptions") and obj.pricing_ratio_exceptions:
        exceptions = obj.pricing_ratio_exceptions.get(country_code, {})

        currency = exceptions.get("currency", None)
        if currency:
            currency = get_cached_currency(currency, cache)

            if currency is None:
                raise ValidationException(
                    translation(
                        lang or "en", en="Currency not found", es="Moneda no encontrada", slug="currency-not-found"
                    ),
                    code=404,
                )

        # Direct price override - Check this FIRST
        if exceptions.get(price_attr) is not None:
            return exceptions[price_attr], None, currency

        # Ratio override
        if exceptions.get("ratio") is not None:
            return price * exceptions["ratio"], exceptions["ratio"], currency

    # Fall back to general ratios
    if country_code in GENERAL_PRICING_RATIOS:
        ratio = GENERAL_PRICING_RATIOS[country_code]["pricing_ratio"]
        return price * ratio, ratio, None

    return price, None, None


def create_seller_reward_coupons(coupons: list[Coupon], original_price: float, buyer_user: User) -> None:
    """
    Create reward coupons for sellers when their coupons are used in payments.

    Creates user-restricted coupons that sellers can use on any plan.

    Args:
        coupons: List of coupons used in the payment
        original_price: The original price before discounts
        buyer_user: The user who made the purchase
    """
    utc_now = timezone.now()

    for coupon in coupons:
        if not coupon.seller or not coupon.seller.user:
            continue

        seller_user = coupon.seller.user

        # Don't create reward for the buyer themselves (already prevented by validation)
        if seller_user == buyer_user:
            continue

        # Calculate reward amount based on coupon's referral settings
        reward_amount = 0
        if coupon.referral_type == Coupon.Referral.PERCENTAGE:
            reward_amount = original_price * coupon.referral_value
        elif coupon.referral_type == Coupon.Referral.FIXED_PRICE:
            reward_amount = coupon.referral_value
        else:
            # No referral reward configured
            continue

        if reward_amount <= 0:
            continue

        # Create a unique slug for the reward coupon
        base_slug = f"reward-{seller_user.id}-{coupon.slug}"
        reward_slug = base_slug
        counter = 1

        while Coupon.objects.filter(slug=reward_slug).exists():
            reward_slug = f"{base_slug}-{counter}"
            counter += 1

        # Create the reward coupon restricted to the seller
        # No plans restriction - can be used with any plan
        reward_coupon = Coupon(
            slug=reward_slug,
            discount_type=Coupon.Discount.FIXED_PRICE,
            discount_value=reward_amount,
            referral_type=Coupon.Referral.NO_REFERRAL,
            referral_value=0,
            auto=False,
            referred_buyer=buyer_user,
            how_many_offers=1,  # Single use
            allowed_user=seller_user,  # Restrict to seller only
            offered_at=utc_now,
            expires_at=utc_now + timedelta(days=90),  # 90 days to use the reward
        )
        reward_coupon.save()

        logger.info(
            f"Created user-restricted reward coupon {reward_coupon.slug} of {reward_amount} "
            f"for seller {seller_user.id} from coupon {coupon.slug}"
        )


def is_plan_paid(plan: Plan) -> bool:
    """
    Check if a plan is paid by examining its pricing structure.

    Args:
        plan: The plan to check

    Returns:
        bool: True if the plan is paid, False if it's free
    """
    if not plan.is_renewable:
        # For non-renewable plans, check if they have financing options
        return plan.financing_options.exists()

    # For renewable plans, check if any pricing field is greater than 0
    return (
        (getattr(plan, "price_per_month", 0) or 0) > 0
        or (getattr(plan, "price_per_quarter", 0) or 0) > 0
        or (getattr(plan, "price_per_half", 0) or 0) > 0
        or (getattr(plan, "price_per_year", 0) or 0) > 0
    )


def is_subscription_paid(subscription: Subscription) -> bool:
    """
    Check if a subscription is paid by examining its plans.

    Args:
        subscription: The subscription to check

    Returns:
        bool: True if the subscription is paid, False if it's free
    """
    for plan in subscription.plans.all():
        if is_plan_paid(plan):
            return True
    return False


def is_plan_financing_paid(plan_financing: PlanFinancing) -> bool:
    """
    Check if a plan financing is paid by examining its plans.

    Args:
        plan_financing: The plan financing to check

    Returns:
        bool: True if the plan financing is paid, False if it's free
    """
    for plan in plan_financing.plans.all():
        if plan.financing_options.exists():
            return True
    return False


def user_has_active_paid_plans(user: User) -> bool:
    """
    Check if a user has any active paid subscriptions or plan financings.

    Args:
        user: The user to check

    Returns:
        bool: True if the user has active paid plans, False otherwise
    """
    # Check for active PAID subscriptions owned by the user or where the user has a seat
    owned_subscriptions = Subscription.objects.filter(user=user, status=Subscription.Status.ACTIVE)
    seated_subscription_ids = SubscriptionSeat.objects.filter(user=user).values_list(
        "billing_team__subscription_id", flat=True
    )
    seat_subscriptions = Subscription.objects.filter(id__in=seated_subscription_ids, status=Subscription.Status.ACTIVE)

    for subscription in owned_subscriptions.union(seat_subscriptions):
        if is_subscription_paid(subscription):
            return True

    return False


def _generate_unique_invite_token() -> str:
    import hashlib
    import os

    token = hashlib.sha512(os.urandom(64)).hexdigest()
    while UserInvite.objects.filter(token=token).exists():
        token = hashlib.sha512(os.urandom(64)).hexdigest()
    return token


def create_subscription_seat_invites(
    *,
    subscription: Subscription,
    service_item: ServiceItem,
    emails: list[str],
    seats: int = 1,
    author: User | None = None,
    lang: str = "en",
) -> list[UserInvite]:
    """Create UserInvite rows and create pending SubscriptionSeat for each email.

    This replaces SubscriptionSeatInvite: we now reserve a seat directly in SubscriptionSeat (user=None, email set)
    and send a UserInvite. On acceptance, the receiver binds the seat to the user and issues consumables.
    """

    if seats < 1:
        raise ValidationException(
            translation(lang, en="Seats must be >= 1", es="Los asientos deben ser >= 1", slug="invalid-seats")
        )

    # Capacity enforcement
    additional = len({e.strip().lower() for e in emails if e and e.strip()})
    if not service_item.can_add_team_member_for_subscription(subscription, additional=additional):
        raise ValidationException(
            translation(
                lang,
                en="No capacity left to invite more team members",
                es="No hay capacidad para invitar más miembros del equipo",
                slug="no-team-capacity",
            ),
            code=400,
        )

    academy = subscription.academy
    created_invites: list[UserInvite] = []

    # Ensure billing team exists for this subscription
    team, _ = SubscriptionBillingTeam.objects.get_or_create(
        subscription=subscription, defaults={"name": f"Team {subscription.id}"}
    )
    if not subscription.supports_billing_team:
        subscription.supports_billing_team = True
        subscription.save(update_fields=["supports_billing_team"])

    for email in {e.strip().lower() for e in emails if e and e.strip()}:
        # Create or reuse an existing pending invite for this email+academy
        invite = UserInvite.objects.filter(email=email, academy=academy, status="PENDING").first()
        if not invite:
            token = _generate_unique_invite_token()
            expires_at = timezone.now() + relativedelta(months=6)

            invite = UserInvite(
                email=email,
                academy=academy,
                author=author,
                token=token,
                expires_at=expires_at,
                status="PENDING",
            )
            invite.save()

            # Send invite email using existing template/flow
            query = urllib.parse.urlencode({"callback": get_app_url()})
            url = os.getenv("API_URL", "") + f"/v1/auth/member/invite/{invite.token}?{query}"
            subject = translation(
                lang, en=f"You are invited to {academy.name}", es=f"Has sido invitado a {academy.name}"
            )

            notify_actions.send_email_message(
                "welcome_academy",
                email,
                {
                    "email": email,
                    "subject": subject,
                    "LINK": url,
                    "FIST_NAME": invite.first_name or "",
                },
                academy=academy,
            )

        # Reserve seat directly in SubscriptionSeat (pending seat)
        seat, created = SubscriptionSeat.objects.get_or_create(
            billing_team=team,
            email=email,
            defaults={
                "user": None,
                "seat_multiplier": seats,
            },
        )

        if created:
            _append_seat_log(seat, "ADDED")

        created_invites.append(invite)

    return created_invites


# ------------------------------
# Team member consumables (per-member issuance from JSON)
# ------------------------------


def _get_team_policy_entries(service_item: ServiceItem) -> list[dict]:
    policy = service_item.team_consumables or {}
    entries = policy.get("allowed")
    if isinstance(entries, list):
        return [e for e in entries if isinstance(e, dict)]
    return []


def _get_target_service_item_for_entry(entry: dict) -> ServiceItem | None:
    slug = entry.get("service_slug")
    unit_type = entry.get("unit_type")
    if not slug:
        return None

    qs = ServiceItem.objects.filter(service__slug=slug)
    if unit_type:
        qs = qs.filter(unit_type=unit_type)
    return qs.order_by("id").first()


def create_team_member_consumables(
    *,
    subscription: Subscription,
    user: User,
    policy_item: ServiceItem,
    seat: SubscriptionSeat | None = None,
    team: SubscriptionBillingTeam | None = None,
    lang: str = "en",
) -> list[Consumable]:
    """Create per-member consumables for a seat user, based on policy_item.team_consumables.

    - Skips entries with missing service_slug
    - Idempotent: if an active consumable already exists for the entry, it won't duplicate
    """
    created: list[Consumable] = []

    if not policy_item.is_team_allowed:
        return created

    entries = _get_team_policy_entries(policy_item)
    utc_now = timezone.now()

    for entry in entries:
        service_slug = entry.get("service_slug")
        if not service_slug:
            logger.warning(
                "Skipping team consumable entry without service_slug for subscription=%s user=%s",
                subscription.id,
                user.id,
            )
            continue

        target_item = _get_target_service_item_for_entry(entry)
        if not target_item:
            logger.warning(
                "No matching ServiceItem for service_slug=%s (unit_type=%s)", service_slug, entry.get("unit_type")
            )
            continue

        # Check if there's already an active consumable for this target
        existing = (
            Consumable.objects.filter(user=user, subscription=subscription, service_item=target_item)
            .filter(Q(valid_until__gte=utc_now) | Q(valid_until=None))
            .exclude(how_many=0)
            .order_by("-id")
            .first()
        )
        if existing:
            continue

        how_many = entry.get("how_many", target_item.how_many)
        unit_type = entry.get("unit_type", target_item.unit_type)
        renew_at = entry.get("renew_at", policy_item.renew_at)
        renew_at_unit = entry.get("renew_at_unit", policy_item.renew_at_unit)

        # Compute valid_until bounded by subscription
        delta = calculate_relative_delta(renew_at, renew_at_unit)
        valid_until = utc_now + delta

        if subscription.next_payment_at and valid_until > subscription.next_payment_at:
            valid_until = subscription.next_payment_at

        if subscription.valid_until and valid_until and valid_until > subscription.valid_until:
            valid_until = subscription.valid_until

        c = Consumable(
            service_item=target_item,
            user=user,
            unit_type=unit_type,
            how_many=how_many,
            valid_until=valid_until,
            subscription=subscription,
            subscription_billing_team=team,
            subscription_seat=seat,
        )
        c.save()
        created.append(c)

        logger.info(
            "Created team consumable id=%s for user=%s subscription=%s service=%s",
            c.id,
            user.id,
            subscription.id,
            target_item.service.slug,
        )

    return created


type SeatLogAction = Literal["ADDED", "REMOVED", "REPLACED"]


class SeatLogEntry(TypedDict):
    email: str
    action: SeatLogAction
    created_at: str


def create_seat_log_entry(seat: SubscriptionSeat, action: SeatLogAction) -> SeatLogEntry:
    utc_now = timezone.now()
    entry = {
        "email": (seat.email or "").strip().lower(),
        "action": action,
        "created_at": utc_now.isoformat().replace("+00:00", "Z"),
    }
    return entry

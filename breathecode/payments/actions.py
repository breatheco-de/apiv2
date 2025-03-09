import os
import re
from datetime import datetime
from functools import lru_cache
from typing import Literal, Optional, Type, TypedDict

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
from breathecode.authenticate.actions import get_user_settings
from breathecode.authenticate.models import UserSetting
from breathecode.media.models import File
from breathecode.payments import tasks
from breathecode.utils import getLogger
from breathecode.utils.validate_conversion_info import validate_conversion_info

from .models import (
    SERVICE_UNITS,
    AcademyService,
    Bag,
    CohortSet,
    Consumable,
    Coupon,
    Currency,
    EventTypeSet,
    Invoice,
    MentorshipServiceSet,
    PaymentMethod,
    Plan,
    PlanFinancing,
    ProofOfPayment,
    Service,
    ServiceItem,
    Subscription,
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
            cohort_set__cohorts__stage__in=["INACTIVE", "PREWORK"],
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
        ).exclude(status__in=["CANCELLED", "DEPRECATED"])
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
        self._add_service_items_to_bag()
        self._validate_just_one_plan()

        self._ask_to_add_plan_and_charge_it_in_the_bag()

        self.bag.save()


def add_items_to_bag(request, bag: Bag, lang: str):
    return BagHandler(request, bag, lang).execute()


def get_amount(bag: Bag, currency: Currency, lang: str) -> tuple[float, float, float, float]:
    user = bag.user
    price_per_month = 0
    price_per_quarter = 0
    price_per_half = 0
    price_per_year = 0

    if not currency:
        currency, _ = Currency.objects.get_or_create(code="USD", name="United States dollar")

    for plan in bag.plans.all():
        if plan.currency != currency:
            bag.plans.remove(plan)
            continue

        must_it_be_charged = ask_to_add_plan_and_charge_it_in_the_bag(plan, user, lang)

        if not bag.how_many_installments and (bag.chosen_period != "NO_SET" or must_it_be_charged):
            price_per_month += plan.price_per_month or 0
            price_per_quarter += plan.price_per_quarter or 0
            price_per_half += plan.price_per_half or 0
            price_per_year += plan.price_per_year or 0

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

            if price_per_month != 0:
                price_per_month += add_on.get_discounted_price(service_item.how_many) * 1

            if price_per_quarter != 0:
                price_per_quarter += add_on.get_discounted_price(service_item.how_many) * 3

            if price_per_half != 0:
                price_per_half += add_on.get_discounted_price(service_item.how_many) * 6

            if price_per_year != 0:
                price_per_year += add_on.get_discounted_price(service_item.how_many) * 12

    return price_per_month, price_per_quarter, price_per_half, price_per_year


def get_amount_by_chosen_period(bag: Bag, chosen_period: str, lang: str) -> float:
    amount = 0

    if chosen_period == "MONTH" and bag.amount_per_month:
        amount = bag.amount_per_month

    elif chosen_period == "QUARTER" and bag.amount_per_quarter:
        amount = bag.amount_per_quarter

    elif chosen_period == "HALF" and bag.amount_per_half:
        amount = bag.amount_per_half

    elif chosen_period == "YEAR" and bag.amount_per_year:
        amount = bag.amount_per_year

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
    bag.currency = last_invoice.currency
    bag.user = subscription.user
    bag.is_recurrent = True
    bag.chosen_period = last_invoice.bag.chosen_period

    if bag.chosen_period == "NO_SET":
        bag.chosen_period = "MONTH"

    bag.save()

    for plan in subscription.plans.all():
        bag.plans.add(plan)

    bag.amount_per_month, bag.amount_per_quarter, bag.amount_per_half, bag.amount_per_year = get_amount(
        bag, last_invoice.currency, lang
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
    bag.currency = last_invoice.currency
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

        if consumable.how_many <= 0:
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


def get_available_coupons(plan: Plan, coupons: Optional[list[str]] = None) -> list[Coupon]:

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
    cou_fields = ("id", "slug", "how_many_offers", "offered_at", "expires_at")

    special_offers = (
        Coupon.objects.filter(*cou_args, auto=True)
        .exclude(Q(how_many_offers=0) | Q(discount_type=Coupon.Discount.NO_DISCOUNT))
        .only(*cou_fields)
    )

    for coupon in special_offers:
        manage_coupon(coupon)

    valid_coupons = (
        Coupon.objects.filter(*cou_args, slug__in=coupons, auto=False).exclude(how_many_offers=0).only(*cou_fields)
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
    coupons = get_available_coupons(plan, data.get("coupons", []))

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

    bag = Bag()
    bag.type = Bag.Type.BAG
    bag.user = user
    bag.currency = academy.main_currency
    bag.status = Bag.Status.PAID
    bag.academy = academy
    bag.is_recurrent = True

    bag.how_many_installments = how_many_installments
    amount = get_discounted_price(option.monthly_price, coupons)
    bag.monthly_price = option.monthly_price

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
    from breathecode.admissions.actions import (
        is_no_saas_student_up_to_date_in_any_cohort,
    )
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

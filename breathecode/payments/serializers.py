import logging
from collections import defaultdict

from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from django.core.exceptions import FieldDoesNotExist
from django.db.models.query_utils import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from breathecode.payments.actions import apply_pricing_ratio
from breathecode.payments.models import (
    AcademyService,
    Bag,
    CohortSet,
    Currency,
    FinancingOption,
    PaymentMethod,
    Plan,
    PlanOffer,
    PlanOfferTranslation,
    Service,
    ServiceItem,
    ServiceItemFeature,
)
from breathecode.utils import serializers, serpy
from breathecode.admissions.models import Cohort, Syllabus
from breathecode.events.models import LiveClass

logger = logging.getLogger(__name__)


class GetCountrySerializer(serpy.Serializer):
    code = serpy.Field()
    name = serpy.Field()


class GetCurrencySmallSerializer(serpy.Serializer):
    code = serpy.Field()
    name = serpy.Field()


class GetCurrencySerializer(GetCurrencySmallSerializer):
    countries = serpy.MethodField()

    def get_countries(self, obj):
        return GetCountrySerializer(obj.countries.all(), many=True).data


class GetPriceSerializer(serpy.Serializer):
    price = serpy.Field()
    currency = GetCurrencySmallSerializer()


class GetAcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()


class GetCohortSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()


class GetSyllabusSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class GetLiveClassSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    hash = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()


class GetPermissionSerializer(serpy.Serializer):
    name = serpy.Field()
    codename = serpy.Field()


class GetGroupSerializer(serpy.Serializer):
    name = serpy.Field()
    permissions = serpy.MethodField()

    def get_permissions(self, obj):
        return GetPermissionSerializer(obj.permissions.all(), many=True).data


class GetServiceSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    slug = serpy.Field()
    # description = serpy.Field()
    owner = serpy.MethodField()
    icon_url = serpy.Field()
    private = serpy.Field()
    groups = serpy.MethodField()
    type = serpy.Field()
    consumer = serpy.Field()
    session_duration = serpy.Field()

    def get_owner(self, obj):
        if obj.owner:
            return GetAcademySmallSerializer(obj.owner, many=False).data
        return None

    def get_groups(self, obj):
        return GetGroupSerializer(obj.groups.all(), many=True).data


class GetServiceSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    slug = serpy.Field()
    # description = serpy.Field()

    owner = serpy.MethodField()
    private = serpy.Field()
    groups = serpy.MethodField()

    def get_owner(self, obj):
        if obj.owner:
            return GetAcademySmallSerializer(obj.owner, many=False).data
        return None

    def get_groups(self, obj):
        return GetGroupSerializer(obj.groups.all(), many=True).data


class GetServiceItemSerializer(serpy.Serializer):
    id = serpy.Field()
    unit_type = serpy.Field()
    how_many = serpy.Field()
    sort_priority = serpy.Field()
    service = GetServiceSmallSerializer()
    is_team_allowed = serpy.Field()
    plan_financing = serpy.MethodField()

    def get_plan_financing(self, obj):
        if not obj.plan_financing:
            return None

        plan = obj.plan_financing
        return {
            "id": plan.id,
            "slug": plan.slug,
            "title": plan.title,
        }


class GetServiceItemFeatureShortSerializer(serpy.Serializer):
    title = serpy.Field()
    description = serpy.Field()
    one_line_desc = serpy.Field()


class GetServiceItemWithFeaturesSerializer(GetServiceItemSerializer):
    features = serpy.MethodField()

    def get_features(self, obj):
        query_args = []
        query_kwargs = {"service_item": obj}
        obj.lang = obj.lang or "en"

        query_args.append(Q(lang=obj.lang) | Q(lang=obj.lang[:2]) | Q(lang__startswith=obj.lang[:2]))

        items = ServiceItemFeature.objects.filter(*query_args, **query_kwargs)
        return GetServiceItemFeatureShortSerializer(items, many=True).data


class GetUserSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()


class GetConsumableSerializer(GetServiceItemSerializer):
    user = GetUserSmallSerializer(many=False)
    valid_until = serpy.Field()


class GetFinancingOptionSerializer(serpy.Serializer):
    id = serpy.Field()
    academy = serpy.MethodField()
    monthly_price = serpy.MethodField()
    how_many_months = serpy.Field()
    pricing_ratio_exceptions = serpy.Field()
    currency = serpy.MethodField()

    def __init__(self, instance=None, many=False, data=None, context=None, **kwargs):
        # Pass instance to super() first
        super().__init__(instance=instance, many=many, data=data, context=context, **kwargs)

        # Access instance data after super().__init__
        # Note: If 'many=True', instance will be a list/queryset.
        # This logic might need adjustment if used with many=True directly,
        # but typically context/cache would be passed externally for 'many'.
        obj_currency = None
        if not many and instance:
            obj_currency = getattr(instance, "currency", None)  # Get currency from the instance being serialized

        self.context = context or {}
        self.lang = self.context.get("lang", "en")  # Use context to get lang
        self.cache = self.context.get("cache", {})  # Use context to get cache

        if obj_currency:  # Check if we got a currency from the object
            slug = obj_currency.code.upper()  # Use code attribute
            if slug not in self.cache:
                self.cache[slug] = obj_currency

    def get_academy(self, obj: FinancingOption):
        if obj.academy:
            return GetAcademySmallSerializer(obj.academy).data
        return None

    def get_currency(self, obj: FinancingOption):
        country_code = self.context.get("country_code")
        if country_code and country_code in obj.pricing_ratio_exceptions:
            currency = obj.currency
            x = obj.pricing_ratio_exceptions[country_code]

            code = x.get("currency")
            if code:
                currency = self.cache.get(code.upper(), Currency.objects.filter(code__iexact=code).first())
                if currency is None:
                    raise ValidationException(
                        translation(
                            self.lang, en="Currency not found", es="Moneda no encontrada", slug="currency-not-found"
                        ),
                        code=404,
                    )

            if currency is None:
                currency, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US dollar", "decimals": 2})

            return GetCurrencySmallSerializer(currency, many=False).data

        return GetCurrencySmallSerializer(obj.currency, many=False).data

    def get_monthly_price(self, obj):
        if not hasattr(self, "context") or not self.context:
            return obj.monthly_price

        country_code = self.context.get("country_code")
        if not country_code:
            return obj.monthly_price

        price, _, _ = apply_pricing_ratio(obj.monthly_price, country_code, obj, cache=self.cache)
        return price


class GetPlanSmallTinySerializer(serpy.Serializer):
    title = serpy.Field()
    slug = serpy.Field()
    status = serpy.Field()
    time_of_life = serpy.Field()
    time_of_life_unit = serpy.Field()
    trial_duration = serpy.Field()
    trial_duration_unit = serpy.Field()


class GetPlanSmallSerializer(GetPlanSmallTinySerializer):
    service_items = serpy.MethodField()
    financing_options = serpy.MethodField()
    has_available_cohorts = serpy.MethodField()
    cohort_set = serpy.MethodField()

    def get_has_available_cohorts(self, obj):
        return bool(obj.cohort_set)

    def get_cohort_set(self, obj):
        if not obj.cohort_set:
            return None
        return GetTinyCohortSetSerializer(obj.cohort_set, many=False).data

    def get_service_items(self, obj):
        return GetServiceItemSerializer(obj.service_items.all(), many=True).data

    def get_financing_options(self, obj):
        if obj.is_renewable:
            return []

        # Pass country_code context to financing options serializer
        context = {}
        if hasattr(self, "context") and self.context:
            context["country_code"] = self.context.get("country_code")

        return GetFinancingOptionSerializer(obj.financing_options.all(), many=True, context=context).data


class GetPlanSerializer(GetPlanSmallSerializer):
    price_per_month = serpy.MethodField()
    price_per_quarter = serpy.MethodField()
    price_per_half = serpy.MethodField()
    price_per_year = serpy.MethodField()
    currency = GetCurrencySmallSerializer()
    is_renewable = serpy.Field()
    has_waiting_list = serpy.Field()
    owner = GetAcademySmallSerializer(required=False, many=False)
    id = serpy.Field()
    pricing_ratio_exceptions = serpy.Field()
    currency = serpy.MethodField()
    add_ons = serpy.MethodField()
    seat_service_price = serpy.MethodField()
    consumption_strategy = serpy.Field()

    def get_seat_service_price(self, obj: Plan):
        if not obj.seat_service_price or obj.seat_service_price.service.type != "SEAT":
            return None

        return GetAcademyServiceSmallSerializer(obj.seat_service_price, many=False).data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = kwargs.get("context", {})
        self.lang = kwargs.get("lang", "en")
        self.cache = kwargs.get("cache", {})

    def get_currency(self, obj: Plan):
        country_code = (self.context.get("country_code") or "").lower()
        if country_code and country_code in obj.pricing_ratio_exceptions:
            currency = obj.currency or obj.owner.main_currency
            x = obj.pricing_ratio_exceptions.get(country_code, {})

            code = x.get("currency")
            if code:
                currency = Currency.objects.filter(code__iexact=code).first()
                if currency is None:
                    raise ValidationException(
                        translation(
                            self.lang, en="Currency not found", es="Moneda no encontrada", slug="currency-not-found"
                        ),
                        code=404,
                    )

            if currency is None:
                currency, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US dollar", "decimals": 2})

            return GetCurrencySmallSerializer(currency, many=False).data

        return GetCurrencySmallSerializer(obj.currency or obj.owner.main_currency, many=False).data

    def get_price_per_month(self, obj: Plan):
        if not hasattr(self, "context") or not self.context:
            return obj.price_per_month

        country_code = self.context.get("country_code")
        if not country_code:
            return obj.price_per_month

        price, _, _ = apply_pricing_ratio(
            obj.price_per_month, country_code, obj, price_attr="price_per_month", cache=self.cache
        )

        return price

    def get_price_per_quarter(self, obj: Plan):
        if not hasattr(self, "context") or not self.context:
            return obj.price_per_quarter

        country_code = self.context.get("country_code")
        if not country_code:
            return obj.price_per_quarter

        price, _, _ = apply_pricing_ratio(
            obj.price_per_quarter, country_code, obj, price_attr="price_per_quarter", cache=self.cache
        )

        return price

    def get_price_per_half(self, obj: Plan):
        if not hasattr(self, "context") or not self.context:
            return obj.price_per_half

        country_code = self.context.get("country_code")
        if not country_code:
            return obj.price_per_half

        price, _, _ = apply_pricing_ratio(
            obj.price_per_half, country_code, obj, price_attr="price_per_half", cache=self.cache
        )

        return price

    def get_price_per_year(self, obj: Plan):
        if not hasattr(self, "context") or not self.context:
            return obj.price_per_year

        country_code = self.context.get("country_code")
        if not country_code:
            return obj.price_per_year

        price, _, _ = apply_pricing_ratio(
            obj.price_per_year, country_code, obj, price_attr="price_per_year", cache=self.cache
        )

        return price

    def get_add_ons(self, obj: Plan):
        context = {}
        if hasattr(self, "context") and self.context:
            context["country_code"] = self.context.get("country_code")

        return GetAcademyServiceSmallReverseSerializer(obj.add_ons.all(), many=True, context=context).data


class GetPlanOfferTranslationSerializer(serpy.Serializer):
    lang = serpy.Field()
    title = serpy.Field()
    description = serpy.Field()
    short_description = serpy.Field()


class GetPlanOfferSerializer(serpy.Serializer):
    original_plan = serpy.MethodField()
    suggested_plan = serpy.MethodField()
    details = serpy.MethodField()
    show_modal = serpy.Field()
    expires_at = serpy.Field()
    live_cohorts = serpy.MethodField()

    def get_original_plan(self, obj: PlanOffer):
        if not obj.original_plan:
            return None
        context = getattr(self, "context", {}) or {}
        return GetPlanSerializer(obj.original_plan, many=False, context=context).data

    def get_suggested_plan(self, obj: PlanOffer):
        if not obj.suggested_plan:
            return None
        context = getattr(self, "context", {}) or {}
        return GetPlanSerializer(obj.suggested_plan, many=False, context=context).data

    def get_details(self, obj):
        query_args = []
        query_kwargs = {"offer": obj}
        obj.lang = obj.lang or "en"

        query_args.append(Q(lang=obj.lang) | Q(lang=obj.lang[:2]) | Q(lang__startswith=obj.lang[:2]))

        item = PlanOfferTranslation.objects.filter(*query_args, **query_kwargs).first()
        if item:
            return GetPlanOfferTranslationSerializer(item, many=False).data

        return None

    def get_live_cohorts(self, obj: PlanOffer):
        if not hasattr(obj, "live_cohorts_syllabus"):
            return []

        syllabi = obj.live_cohorts_syllabus.all()
        if not syllabi:
            return []

        now = timezone.now()
        response = []

        for syllabus in syllabi:
            classes = (
                LiveClass.objects.filter(
                    cohort_time_slot__cohort__syllabus_version__syllabus=syllabus,
                    starting_at__gte=now,
                )
                .select_related(
                    "cohort_time_slot__cohort__academy",
                )
                .order_by("starting_at")
            )

            cohorts_map: dict[int, dict[str, object]] = {}
            for live_class in classes:
                cohort = live_class.cohort_time_slot.cohort
                if cohort.id not in cohorts_map:
                    cohorts_map[cohort.id] = {
                        "id": cohort.id,
                        "slug": cohort.slug,
                        "name": cohort.name,
                        "kickoff_date": cohort.kickoff_date,
                        "ending_date": cohort.ending_date,
                        "timezone": cohort.timezone,
                        "academy": GetAcademySmallSerializer(cohort.academy, many=False).data if cohort.academy else None,
                        "live_classes": [],
                    }

                entry = cohorts_map[cohort.id]["live_classes"]
                if len(entry) < 10:
                    entry.append(
                        {
                            "id": live_class.id,
                            "hash": live_class.hash,
                            "starting_at": live_class.starting_at,
                            "ending_at": live_class.ending_at,
                        }
                    )

            response.append(
                {
                    "syllabus": GetSyllabusSmallSerializer(syllabus, many=False).data,
                    "cohorts": list(cohorts_map.values()),
                }
            )

        return response


class GetInvoiceSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    amount = serpy.Field()
    currency = GetCurrencySmallSerializer(many=False)
    paid_at = serpy.Field()
    status = serpy.Field()
    user = GetUserSmallSerializer(many=False)


class GetMentorshipServiceSerializer(serpy.Serializer):

    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    description = serpy.Field()
    logo_url = serpy.Field()
    duration = serpy.Field()
    max_duration = serpy.Field()
    language = serpy.Field()
    missed_meeting_duration = serpy.Field()
    status = serpy.Field()
    academy = GetAcademySmallSerializer(many=False)


class GetSellerSerializer(serpy.Serializer):

    name = serpy.Field()
    user = GetUserSmallSerializer(many=False, required=False)
    is_hidden = serpy.Field()
    is_active = serpy.Field()


class GetCouponSerializer(serpy.Serializer):

    slug = serpy.Field()
    discount_type = serpy.Field()
    discount_value = serpy.Field()
    referral_type = serpy.Field()
    referral_value = serpy.Field()
    auto = serpy.Field()
    allowed_user = GetUserSmallSerializer(many=False, required=False)
    offered_at = serpy.Field()
    expires_at = serpy.Field()


class GetCouponWithPlansSerializer(serpy.Serializer):

    slug = serpy.Field()
    discount_type = serpy.Field()
    discount_value = serpy.Field()
    referral_type = serpy.Field()
    referral_value = serpy.Field()
    auto = serpy.Field()
    plans = serpy.MethodField()
    offered_at = serpy.Field()
    expires_at = serpy.Field()

    def get_plans(self, obj):
        return GetPlanSmallSerializer(obj.plans.all(), many=True).data


class GetAcademyServiceSmallReverseSerializer(serpy.Serializer):
    id = serpy.Field()
    academy = GetAcademySmallSerializer()
    service = GetServiceSmallSerializer()
    price_per_unit = serpy.MethodField()
    bundle_size = serpy.Field()
    max_items = serpy.Field()
    max_amount = serpy.Field()
    discount_ratio = serpy.Field()
    pricing_ratio_exceptions = serpy.Field()
    currency = serpy.MethodField()
    plan_financing = serpy.MethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = kwargs.get("context", {})
        self.lang = kwargs.get("lang", "en")
        self.cache = kwargs.get("cache", {})

    def get_currency(self, obj: Plan):
        country_code = self.context.get("country_code")
        if country_code and country_code in obj.pricing_ratio_exceptions:
            currency = obj.currency
            x = obj.pricing_ratio_exceptions[country_code]

            code = x.get("currency")
            if code:
                currency = Currency.objects.filter(code__iexact=code).first()
                if currency is None:
                    raise ValidationException(
                        translation(
                            self.lang, en="Currency not found", es="Moneda no encontrada", slug="currency-not-found"
                        ),
                        code=404,
                    )

            if currency is None:
                currency, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US dollar", "decimals": 2})

            return GetCurrencySmallSerializer(currency, many=False).data

        return GetCurrencySmallSerializer(obj.currency, many=False).data

    def get_price_per_unit(self, obj):
        if not hasattr(self, "context") or not self.context:
            return obj.price_per_unit

        country_code = self.context.get("country_code")
        if not country_code:
            return obj.price_per_unit

        price, _, _ = apply_pricing_ratio(obj.price_per_unit, country_code, obj)
        return price

    def get_plan_financing(self, obj):
        service_item = (
            ServiceItem.objects.filter(service=obj.service, plan_financing__isnull=False).select_related("plan_financing").first()
        )
        if not service_item or not service_item.plan_financing:
            return None

        plan = service_item.plan_financing
        return {
            "id": plan.id,
            "slug": plan.slug,
            "title": plan.title,
        }


class GetAcademyServiceSmallSerializer(GetAcademyServiceSmallReverseSerializer):
    available_mentorship_service_sets = serpy.MethodField()
    available_event_type_sets = serpy.MethodField()

    def get_available_mentorship_service_sets(self, obj):
        items = obj.available_mentorship_service_sets.all()
        from breathecode.payments.serializers import GetMentorshipServiceSetSmallSerializer

        return GetMentorshipServiceSetSmallSerializer(items, many=True).data

    def get_available_event_type_sets(self, obj):
        items = obj.available_event_type_sets.all()
        from breathecode.payments.serializers import GetEventTypeSetSmallSerializer

        return GetEventTypeSetSmallSerializer(items, many=True).data


class POSTAcademyServiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = AcademyService
        exclude = ()

    def validate(self, data):
        if "price_per_unit" not in data:
            raise ValidationError("You must specify a price per unit")

        return data

    def create(self, validated_data):
        academy_service = super().create(validated_data)

        return academy_service


class PUTAcademyServiceSerializer(serializers.ModelSerializer):
    currency = serializers.PrimaryKeyRelatedField(read_only=True)
    academy = serializers.PrimaryKeyRelatedField(read_only=True)
    service = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AcademyService
        fields = "__all__"

    def validate(self, data):

        return data

    def update(self, instance, validated_data):

        academy_service = super().update(instance, validated_data)

        return academy_service


class GetMentorshipServiceSetSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    academy = GetAcademySmallSerializer(many=False)
    mentorship_services = serpy.MethodField()

    def get_mentorship_services(self, obj):
        return GetMentorshipServiceSerializer(obj.mentorship_services.filter(), many=True).data


class GetMentorshipServiceSetSerializer(GetMentorshipServiceSetSmallSerializer):
    academy_services = serpy.MethodField()

    def get_academy_services(self, obj):
        items = AcademyService.objects.filter(available_mentorship_service_sets=obj)
        return GetAcademyServiceSmallReverseSerializer(items, many=True).data


class GetCohortSetSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    academy = GetAcademySmallSerializer(many=False)
    cohorts = serpy.MethodField()

    def get_cohorts(self, obj):
        return GetCohortSerializer(obj.cohorts.filter(), many=True).data


class GetTinyCohortSetSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    cohorts = serpy.MethodField()

    def get_cohorts(self, obj):
        return GetCohortSerializer(obj.cohorts.filter(), many=True).data


class CohortSetSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating CohortSet."""

    class Meta:
        model = CohortSet
        fields = ("slug",)


class GetEventTypeSerializer(serpy.Serializer):

    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    description = serpy.Field()
    icon_url = serpy.Field()
    lang = serpy.Field()
    allow_shared_creation = serpy.Field()


class GetEventTypeSetSmallSerializer(serpy.Serializer):

    id = serpy.Field()
    slug = serpy.Field()
    academy = GetAcademySmallSerializer(many=False)
    event_types = serpy.MethodField()

    def get_event_types(self, obj):
        return GetEventTypeSerializer(obj.event_types.filter(), many=True).data


class GetEventTypeSetSerializer(GetEventTypeSetSmallSerializer):
    academy_services = serpy.MethodField()

    def get_academy_services(self, obj):
        items = AcademyService.objects.filter(available_event_type_sets=obj)
        return GetAcademyServiceSmallReverseSerializer(items, many=True).data


class GetAbstractIOweYouSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    status = serpy.Field()
    user = GetUserSmallSerializer(many=False)
    plans = serpy.ManyToManyField(GetPlanSmallTinySerializer(attr="plans", many=True))
    selected_cohort_set = GetCohortSetSerializer(many=False, required=False)


class GetBagSerializer(serpy.Serializer):
    id = serpy.Field()
    service_items = serpy.MethodField()
    plans = serpy.MethodField()
    coupons = serpy.MethodField()
    status = serpy.Field()
    type = serpy.Field()
    is_recurrent = serpy.Field()
    was_delivered = serpy.Field()
    amount_per_month = serpy.Field()
    amount_per_quarter = serpy.Field()
    amount_per_half = serpy.Field()
    amount_per_year = serpy.Field()
    discounted_amount_per_month = serpy.Field()
    discounted_amount_per_quarter = serpy.Field()
    discounted_amount_per_half = serpy.Field()
    discounted_amount_per_year = serpy.Field()

    token = serpy.Field()
    seat_service_item = serpy.MethodField()
    expires_at = serpy.Field()

    def get_service_items(self, obj):
        return GetServiceItemSerializer(obj.service_items.filter(), many=True).data

    def get_seat_service_item(self, obj: Bag):
        if not obj.seat_service_item or obj.seat_service_item.service.type != "SEAT":
            return None

        return GetServiceItemSerializer(obj.seat_service_item, many=False).data

    def get_plans(self, obj):
        return GetPlanSmallSerializer(obj.plans.filter(), many=True).data

    def get_coupons(self, obj):
        return GetCouponSerializer(obj.coupons.filter(), many=True).data


class GetInvoiceSerializer(GetInvoiceSmallSerializer):
    id = serpy.Field()
    amount = serpy.Field()
    paid_at = serpy.Field()
    status = serpy.Field()
    externally_managed = serpy.Field()
    currency = GetCurrencySmallSerializer()
    bag = GetBagSerializer(many=False)

    amount_refunded = serpy.Field()
    refund_stripe_id = serpy.Field()
    refunded_at = serpy.Field()


class GetAbstractIOweYouSerializer(serpy.Serializer):

    id = serpy.Field()
    status = serpy.Field()
    status_message = serpy.Field()

    user = GetUserSmallSerializer(many=False)
    academy = GetAcademySmallSerializer(many=False)

    selected_cohort_set = GetCohortSetSerializer(many=False, required=False)
    selected_mentorship_service_set = GetMentorshipServiceSetSerializer(many=False, required=False)
    selected_event_type_set = GetEventTypeSetSerializer(many=False, required=False)

    plans = serpy.ManyToManyField(GetPlanSmallSerializer(attr="plans", many=True))
    invoices = serpy.ManyToManyField(GetInvoiceSerializer(attr="invoices", many=True))

    next_payment_at = serpy.Field()
    valid_until = serpy.Field()

    # Billing team and seat information
    has_billing_team = serpy.MethodField()
    seats_count = serpy.MethodField()
    seats_limit = serpy.MethodField()

    def get_has_billing_team(self, obj):
        """Check if this financing/subscription has a billing team."""
        return hasattr(obj, "subscriptionbillingteam")

    def get_seats_count(self, obj):
        """Get number of active seats in the billing team."""
        if hasattr(obj, "subscriptionbillingteam"):
            return obj.subscriptionbillingteam.seats.filter(is_active=True).count()
        return None

    def get_seats_limit(self, obj):
        """Get total seat limit for the billing team."""
        if hasattr(obj, "subscriptionbillingteam"):
            return obj.subscriptionbillingteam.seats_limit
        return None


class GetPlanFinancingSerializer(GetAbstractIOweYouSerializer):
    plan_expires_at = serpy.Field()
    monthly_price = serpy.Field()
    how_many_installments = serpy.Field()


class GetSubscriptionHookSerializer(GetAbstractIOweYouSerializer):
    paid_at = serpy.Field()
    is_refundable = serpy.Field()

    pay_every = serpy.Field()
    pay_every_unit = serpy.Field()


class GetSubscriptionSerializer(GetAbstractIOweYouSerializer):
    paid_at = serpy.Field()
    created_at = serpy.Field()
    is_refundable = serpy.Field()

    pay_every = serpy.Field()
    pay_every_unit = serpy.Field()

    service_items = serpy.MethodField()

    def get_service_items(self, obj):
        return GetServiceItemSerializer(obj.service_items.filter(), many=True).data


class ServiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Service
        fields = "__all__"

    def validate(self, attrs):
        return attrs


class ServiceItemSerializer(serializers.ModelSerializer):
    status_fields = ["unit_type"]

    class Meta:
        model = ServiceItem
        fields = "__all__"

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        # Use the model's get_or_create_for_service method which encapsulates
        # the business logic for ServiceItem uniqueness
        service_item, created = ServiceItem.get_or_create_for_service(
            service=validated_data.get("service"),
            how_many=validated_data.get("how_many"),
            unit_type=validated_data.get("unit_type", "UNIT"),
            is_renewable=validated_data.get("is_renewable", False),
            is_team_allowed=validated_data.get("is_team_allowed", False),
            renew_at=validated_data.get("renew_at", 1),
            renew_at_unit=validated_data.get("renew_at_unit", "MONTH"),
            sort_priority=validated_data.get("sort_priority", 1),
        )
        return service_item


class PlanSerializer(serializers.ModelSerializer):
    status_fields = ["status", "renew_every_unit", "trial_duration_unit", "time_of_life_unit"]

    class Meta:
        model = Plan
        fields = "__all__"

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        m2m_fields = {}

        for key in list(validated_data.keys()):
            try:
                field = Plan._meta.get_field(key)
            except FieldDoesNotExist:  # pragma: no cover - defensive safeguard
                continue

            if field.many_to_many:
                m2m_fields[key] = validated_data.pop(key)

        instance = Plan.objects.create(**validated_data)

        for key, value in m2m_fields.items():
            relation = getattr(instance, key)

            if value is None:
                relation.clear()
                continue

            relation.set(value)

        return instance

    def update(self, instance, validated_data):
        m2m_updates = {}

        for key, value in validated_data.items():
            try:
                field = instance._meta.get_field(key)
            except FieldDoesNotExist:  # pragma: no cover - defensive safeguard
                setattr(instance, key, value)
                continue

            if field.many_to_many:
                m2m_updates[key] = value
                continue

            setattr(instance, key, value)

        instance.save()

        for key, value in m2m_updates.items():
            relation = getattr(instance, key)

            if value is None:
                relation.clear()
                continue

            relation.set(value)

        return instance


class PutPlanSerializer(PlanSerializer):
    status_fields = ["status", "renew_every_unit", "trial_duration_unit", "time_of_life_unit"]

    class Meta:
        model = Plan
        fields = "__all__"

    def validate(self, attrs):
        return attrs


class FinancingOptionSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating FinancingOption"""

    class Meta:
        model = FinancingOption
        fields = ["id", "academy", "monthly_price", "how_many_months", "currency", "pricing_ratio_exceptions"]
        read_only_fields = ["id", "academy"]

    def validate_monthly_price(self, value):
        if value <= 0:
            raise ValidationException(
                translation(
                    en="Monthly price must be greater than 0",
                    es="El precio mensual debe ser mayor que 0",
                ),
                slug="invalid-monthly-price",
                code=400,
            )
        return value

    def validate_how_many_months(self, value):
        if value <= 0:
            raise ValidationException(
                translation(
                    en="Number of months must be greater than 0",
                    es="El número de meses debe ser mayor que 0",
                ),
                slug="invalid-months",
                code=400,
            )
        return value

    def create(self, validated_data):
        from breathecode.admissions.models import Academy

        # Get academy from validated_data or from save() kwargs
        # The view calls serializer.save(academy_id=academy_id)
        academy_id = validated_data.pop("academy_id", None)
        academy = validated_data.get("academy")

        # Convert academy_id to Academy instance if needed
        if academy_id and not academy:
            academy = Academy.objects.filter(id=academy_id).first()
            if not academy:
                raise ValidationException(
                    translation(
                        en="Academy not found",
                        es="Academia no encontrada",
                    ),
                    slug="academy-not-found",
                    code=404,
                )

        # Use the model's get_or_create_for_academy method which encapsulates
        # the business logic for FinancingOption uniqueness
        financing_option, created = FinancingOption.get_or_create_for_academy(
            academy=academy,
            monthly_price=validated_data.get("monthly_price"),
            currency=validated_data.get("currency"),
            how_many_months=validated_data.get("how_many_months"),
            pricing_ratio_exceptions=validated_data.get("pricing_ratio_exceptions"),
        )
        return financing_option

    def update(self, instance, validated_data):
        for key in validated_data:
            setattr(instance, key, validated_data[key])
        instance.save()
        return instance


class GetPaymentMethod(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    is_backed = serpy.Field()
    lang = serpy.Field()
    is_credit_card = serpy.Field()
    is_crypto = serpy.Field()
    description = serpy.Field()
    third_party_link = serpy.Field()
    academy = GetAcademySmallSerializer(required=False, many=False)
    currency = GetCurrencySmallSerializer(required=False, many=False)
    included_country_codes = serpy.Field()
    visibility = serpy.Field()
    deprecated = serpy.Field()


class PaymentMethodSerializer(serializers.ModelSerializer):
    currency = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Currency.objects.all(),
        required=False,
        allow_null=True,
    )
    academy = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PaymentMethod
        fields = (
            "id",
            "title",
            "description",
            "third_party_link",
            "is_backed",
            "lang",
            "is_credit_card",
            "currency",
            "academy",
            "included_country_codes",
            "visibility",
            "deprecated",
        )


class GetConsumptionSessionSerializer(serpy.Serializer):
    id = serpy.Field()
    operation_code = serpy.Field()
    eta = serpy.Field()
    duration = serpy.Field()
    how_many = serpy.Field()
    status = serpy.Field()
    was_discounted = serpy.Field()
    request = serpy.Field()
    path = serpy.Field()
    related_id = serpy.Field()
    related_slug = serpy.Field()
    user = GetUserSmallSerializer(required=False)


class BillingTeamAutoRechargeSerializer(serializers.Serializer):
    """
    Input serializer for updating billing team auto-recharge settings.

    Used for PUT /v2/payments/subscription/{id}/billing-team
    """

    auto_recharge_enabled = serializers.BooleanField(required=False)
    recharge_threshold_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=0,
        help_text="Balance threshold to trigger recharge (in subscription currency)",
    )
    recharge_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=0,
        help_text="Amount to recharge when threshold is reached",
    )
    max_period_spend = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=0,
        help_text="Maximum spending per monthly period (null = unlimited)",
    )

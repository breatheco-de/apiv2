import logging

from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from django.db.models.query_utils import Q
from rest_framework.exceptions import ValidationError

from breathecode.payments.actions import apply_pricing_ratio
from breathecode.payments.models import (
    AcademyService,
    Currency,
    FinancingOption,
    PaymentMethod,
    Plan,
    PlanOfferTranslation,
    Service,
    ServiceItem,
    ServiceItemFeature,
)
from breathecode.utils import serializers, serpy

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


class GetPermissionSerializer(serpy.Serializer):
    name = serpy.Field()
    codename = serpy.Field()


class GetGroupSerializer(serpy.Serializer):
    name = serpy.Field()
    permissions = serpy.MethodField()

    def get_permissions(self, obj):
        return GetPermissionSerializer(obj.permissions.all(), many=True).data


class GetServiceSmallSerializer(serpy.Serializer):
    title = serpy.Field()
    slug = serpy.Field()
    # description = serpy.Field()
    # owner = GetAcademySmallSerializer(many=False)
    icon_url = serpy.Field()
    private = serpy.Field()
    groups = serpy.MethodField()

    def get_groups(self, obj):
        return GetGroupSerializer(obj.groups.all(), many=True).data


class GetServiceSerializer(serpy.Serializer):
    title = serpy.Field()
    slug = serpy.Field()
    # description = serpy.Field()
    currency = GetCurrencySmallSerializer(many=False)

    owner = GetAcademySmallSerializer(many=False)
    private = serpy.Field()
    groups = serpy.MethodField()

    def get_groups(self, obj):
        return GetGroupSerializer(obj.groups.all(), many=True).data


class GetServiceItemSerializer(serpy.Serializer):
    unit_type = serpy.Field()
    how_many = serpy.Field()
    sort_priority = serpy.Field()
    service = GetServiceSmallSerializer()


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
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()


class GetConsumableSerializer(GetServiceItemSerializer):
    user = GetUserSmallSerializer(many=False)
    valid_until = serpy.Field()


class GetFinancingOptionSerializer(serpy.Serializer):
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


class GetPlanSmallSerializer(serpy.Serializer):
    # title = serpy.Field()
    slug = serpy.Field()
    # description = serpy.Field()
    status = serpy.Field()
    time_of_life = serpy.Field()
    time_of_life_unit = serpy.Field()
    trial_duration = serpy.Field()
    trial_duration_unit = serpy.Field()
    service_items = serpy.MethodField()
    financing_options = serpy.MethodField()
    has_available_cohorts = serpy.MethodField()

    def get_has_available_cohorts(self, obj):
        return bool(obj.cohort_set)

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


class GetPlanOfferTranslationSerializer(serpy.Serializer):
    lang = serpy.Field()
    title = serpy.Field()
    description = serpy.Field()
    short_description = serpy.Field()


class GetPlanOfferSerializer(serpy.Serializer):
    original_plan = GetPlanSerializer(required=False, many=False)
    suggested_plan = GetPlanSerializer(required=False, many=False)
    details = serpy.MethodField()
    show_modal = serpy.Field()
    expires_at = serpy.Field()

    def get_details(self, obj):
        query_args = []
        query_kwargs = {"offer": obj}
        obj.lang = obj.lang or "en"

        query_args.append(Q(lang=obj.lang) | Q(lang=obj.lang[:2]) | Q(lang__startswith=obj.lang[:2]))

        item = PlanOfferTranslation.objects.filter(*query_args, **query_kwargs).first()
        if item:
            return GetPlanOfferTranslationSerializer(item, many=False).data

        return None


class GetInvoiceSmallSerializer(serpy.Serializer):
    amount = serpy.Field()
    currency = GetCurrencySmallSerializer(many=False)
    paid_at = serpy.Field()
    status = serpy.Field()
    user = GetUserSmallSerializer(many=False)


class GetInvoiceSerializer(GetInvoiceSmallSerializer):
    amount = serpy.Field()
    paid_at = serpy.Field()
    status = serpy.Field()
    currency = GetCurrencySmallSerializer()


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
    offered_at = serpy.Field()
    expires_at = serpy.Field()


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

        price, _ = apply_pricing_ratio(obj.price_per_unit, country_code, obj)
        return price


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
    token = serpy.Field()
    expires_at = serpy.Field()

    def get_service_items(self, obj):
        return GetServiceItemSerializer(obj.service_items.filter(), many=True).data

    def get_plans(self, obj):
        return GetPlanSmallSerializer(obj.plans.filter(), many=True).data

    def get_coupons(self, obj):
        return GetCouponSerializer(obj.coupons.filter(), many=True).data


class ServiceSerializer(serializers.Serializer):

    class Meta:
        model = Service
        fields = "__all__"

    def validate(self, attrs):
        return attrs


class ServiceItemSerializer(serializers.Serializer):
    status_fields = ["unit_type"]

    class Meta:
        model = ServiceItem
        fields = "__all__"

    def validate(self, attrs):
        return attrs


class PlanSerializer(serializers.ModelSerializer):
    status_fields = ["status", "renew_every_unit", "trial_duration_unit", "time_of_life_unit"]

    class Meta:
        model = Plan
        fields = "__all__"

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        return Plan.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for key in validated_data:
            setattr(instance, key, validated_data[key])

        instance.save()
        return instance


class PutPlanSerializer(PlanSerializer):
    status_fields = ["status", "renew_every_unit", "trial_duration_unit", "time_of_life_unit"]

    class Meta:
        model = Plan
        fields = "__all__"

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        return Plan.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for key in validated_data:
            setattr(instance, key, validated_data[key])

        instance.save()
        return instance


class GetPaymentMethod(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    is_credit_card = serpy.Field()
    description = serpy.Field()
    third_party_link = serpy.Field()
    academy = GetAcademySmallSerializer(required=False, many=False)
    currency = GetCurrencySmallSerializer(required=False, many=False)
    included_country_codes = serpy.Field()


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
            "lang",
            "is_credit_card",
            "currency",
            "academy",
            "included_country_codes",
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

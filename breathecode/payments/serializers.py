import logging

from django.db.models.query_utils import Q
from rest_framework.exceptions import ValidationError

from breathecode.payments.models import (
    AcademyService,
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
    # title = serpy.Field()
    monthly_price = serpy.Field()
    how_many_months = serpy.Field()
    currency = GetCurrencySmallSerializer()


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

        return GetFinancingOptionSerializer(obj.financing_options.all(), many=True).data


class GetPlanSerializer(GetPlanSmallSerializer):
    price_per_month = serpy.Field()
    price_per_quarter = serpy.Field()
    price_per_half = serpy.Field()
    price_per_year = serpy.Field()
    currency = GetCurrencySmallSerializer()
    is_renewable = serpy.Field()
    has_waiting_list = serpy.Field()
    owner = GetAcademySmallSerializer(required=False, many=False)


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


class GetAcademyServiceSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    academy = GetAcademySmallSerializer(many=False)
    service = GetServiceSmallSerializer()
    currency = GetCurrencySmallSerializer()
    price_per_unit = serpy.Field()
    bundle_size = serpy.Field()
    max_items = serpy.Field()
    max_amount = serpy.Field()
    discount_ratio = serpy.Field()


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
        return GetAcademyServiceSmallSerializer(items, many=True).data


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
        return GetAcademyServiceSmallSerializer(items, many=True).data


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


class GetSubscriptionHookSerializer(GetAbstractIOweYouSerializer):
    paid_at = serpy.Field()
    is_refundable = serpy.Field()

    pay_every = serpy.Field()
    pay_every_unit = serpy.Field()


class GetSubscriptionSerializer(GetAbstractIOweYouSerializer):
    paid_at = serpy.Field()
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

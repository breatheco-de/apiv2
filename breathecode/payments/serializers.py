import logging
import serpy
from breathecode.admissions.models import Cohort
from breathecode.payments.models import Plan, Service, ServiceItem, ServiceItemFeature, Subscription
from django.db.models.query_utils import Q

from breathecode.utils import serializers, custom_serpy
from django.utils import timezone

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


class GetAcademySerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()


class GetCohortSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()


class GetMentorshipServiceSerializer(serpy.Serializer):
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
    # title = serpy.Field()
    slug = serpy.Field()
    # description = serpy.Field()

    price_per_unit = serpy.Field()

    # owner = GetAcademySerializer(many=False)
    private = serpy.Field()
    groups = serpy.MethodField()

    def get_groups(self, obj):
        return GetGroupSerializer(obj.groups.all(), many=True).data


class GetServiceSerializer(custom_serpy.Serializer):
    # title = serpy.Field()
    slug = serpy.Field()
    # description = serpy.Field()

    price_per_unit = serpy.Field()
    currency = GetCurrencySmallSerializer(many=False)

    owner = GetAcademySerializer(many=False)
    private = serpy.Field()
    groups = serpy.MethodField()
    cohorts = serpy.MethodField()
    mentorship_services = serpy.MethodField()
    cohorts = custom_serpy.MethodField()

    def get_groups(self, obj):
        return GetGroupSerializer(obj.groups.all(), many=True).data

    def get_cohorts(self, obj):
        return GetCohortSerializer(obj.cohorts.all(), many=True).data

    def get_mentorship_services(self, obj):
        return GetMentorshipServiceSerializer(obj.mentorship_services.all(), many=True).data

    def get_cohorts(self, obj):
        utc_now = timezone.now()
        kwargs = {}
        if 'academy' in self.context and self.context['academy_id'] and (isinstance(
                self.context['academy_id'], int) or self.context['academy_id'].isnumeric()):
            kwargs['academy__id'] = int(self.context['academy'])

        elif 'academy' in self.context and self.context['academy_id']:
            kwargs['academy__slug'] = self.context['academy']

        cohorts = Cohort.objects.none()

        service = obj
        payment_service_schedulers = PaymentServiceScheduler.objects.filter(service=service)

        for schedule in payment_service_schedulers:
            all = schedule.cohorts.filter(remote_available=True,
                                          academy__main_currency__isnull=False,
                                          academy__available_as_saas=True,
                                          **kwargs).exclude(Q(stage='DELETED') | Q(stage='ENDED'))

            never_ends = all.filter(never_ends=True)
            upcoming = all.filter(
                never_ends=False,
                kickoff_date__gt=utc_now).exclude(Q(stage='FINAL_PROJECT') | Q(stage='STARTED'))

            cohorts |= never_ends
            cohorts |= upcoming

        cohorts = cohorts.distinct()

        return GetCohortSerializer(cohorts, many=True).data


class GetServiceItemSerializer(serpy.Serializer):
    unit_type = serpy.Field()
    how_many = serpy.Field()
    service = GetServiceSmallSerializer()


class GetServiceItemFeatureShortSerializer(serpy.Serializer):
    description = serpy.Field()
    one_line_desc = serpy.Field()


class GetServiceItemWithFeaturesSerializer(GetServiceItemSerializer):
    features = serpy.MethodField()

    def get_features(self, obj):
        query_args = []
        query_kwargs = {'service_item': obj}
        obj.lang = obj.lang or 'en'

        if '-' in obj.lang:
            query_args.append(Q(lang=obj.lang) | Q(lang=obj.lang[:2]))

        else:
            query_kwargs['lang'] = obj.lang

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


class GetPlanSmallSerializer(custom_serpy.Serializer):
    # title = serpy.Field()
    slug = serpy.Field()
    # description = serpy.Field()
    status = serpy.Field()
    trial_duration = serpy.Field()
    trial_duration_unit = serpy.Field()
    service_items = serpy.MethodField()
    financing_options = serpy.MethodField()

    def get_service_items(self, obj):
        return GetServiceItemSerializer(obj.service_items.all(), many=True).data

    def get_financing_options(self, obj):
        return GetFinancingOptionSerializer(obj.financing_options.all(), many=True).data


class GetPlanSerializer(GetPlanSmallSerializer):
    price_per_month = serpy.Field()
    price_per_quarter = serpy.Field()
    price_per_half = serpy.Field()
    price_per_year = serpy.Field()
    currency = GetCurrencySmallSerializer()
    owner = GetAcademySerializer()


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


class GetSubscriptionSerializer(serpy.Serializer):
    paid_at = serpy.Field()
    status = serpy.Field()
    is_cancellable = serpy.Field()
    is_refundable = serpy.Field()
    is_recurrent = serpy.Field()

    invoices = GetInvoiceSerializer(many=True)
    valid_until = serpy.Field()
    last_renew = serpy.Field()

    pay_every = serpy.Field()
    pay_every_unit = serpy.Field()
    renew_every = serpy.Field()
    renew_every_unit = serpy.Field()

    user = GetUserSmallSerializer(many=False)
    services = GetServiceItemSerializer(many=True)
    plans = GetPlanSerializer(many=True)


class GetCreditSerializer(serpy.Serializer):
    valid_until = serpy.Field()
    is_free_trial = serpy.Field()
    services = GetConsumableSerializer(many=True)
    invoice = GetInvoiceSerializer(many=False)


class GetBagSerializer(serpy.Serializer):
    service_items = serpy.MethodField()
    plans = serpy.MethodField()
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


class GetCheckingSerializer(GetInvoiceSmallSerializer):
    amount = GetServiceItemSerializer(many=True)
    token = GetPlanSerializer(many=True)
    expires_at = GetPlanSerializer(many=True)

    services = GetServiceItemSerializer(many=True)
    plans = GetPlanSerializer(many=True)


class ServiceSerializer(serializers.Serializer):

    class Meta:
        model = Service
        fields = '__all__'

    def validate(self, attrs):
        return attrs


class ServiceItemSerializer(serializers.Serializer):
    status_fields = ['unit_type']

    class Meta:
        model = ServiceItem
        fields = '__all__'

    def validate(self, attrs):
        return attrs


class PlanSerializer(serializers.Serializer):
    status_fields = ['status', 'renew_every_unit', 'trial_duration_unit']

    class Meta:
        model = Plan
        fields = '__all__'

    def validate(self, attrs):
        return attrs

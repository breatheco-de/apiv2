import logging
import serpy
from breathecode.payments.models import Plan, Price, Service, ServiceItem, Subscription

from breathecode.utils import serializers

logger = logging.getLogger(__name__)


class GetCountrySerializer(serpy.Serializer):
    code = serpy.Field()
    name = serpy.Field()


class GetCurrencySmallSerializer(serpy.Serializer):
    code = serpy.Field()
    name = serpy.Field()


class GetCurrencySerializer(GetCurrencySmallSerializer):
    countries = GetCountrySerializer(many=True)


class GetPriceSerializer(serpy.Serializer):
    price = serpy.Field()
    currency = GetCurrencySmallSerializer(many=False)


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
    permissions = GetPermissionSerializer(many=True)


class GetServiceSerializer(serpy.Serializer):
    title = serpy.Field()
    slug = serpy.Field()
    description = serpy.Field()
    prices = GetPriceSerializer(many=True)
    owner = GetAcademySerializer(many=False)
    private = serpy.Field()
    groups = GetGroupSerializer(many=True)
    cohorts = GetCohortSerializer(many=True)
    mentorship_services = GetMentorshipServiceSerializer(many=True)


class GetServiceItemSerializer(serpy.Serializer):
    service = GetServiceSerializer(many=False)
    unit_type = serpy.Field()
    how_many = serpy.Field()


class GetUserSmallSerializer(serpy.Serializer):
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()


class GetConsumableSerializer(GetServiceItemSerializer):
    user = GetUserSmallSerializer(many=False)
    valid_until = serpy.Field()


class GetPlanSerializer(serpy.Serializer):
    title = serpy.Field()
    slug = serpy.Field()
    description = serpy.Field()
    status = serpy.Field()
    prices = GetPriceSerializer(many=True)
    renew_every = serpy.Field()
    renew_every_unit = serpy.Field()
    trial_duration = serpy.Field()
    trial_duration_unit = serpy.Field()
    services = GetServiceItemSerializer(many=True)
    owner = GetAcademySerializer(many=False)
    # services = serpy.MethodField()

    # def get_services(self, obj):
    #     return obj.role.slug


class GetInvoiceSmallSerializer(serpy.Serializer):
    amount = serpy.Field()
    currency = GetCurrencySmallSerializer(many=False)
    paid_at = serpy.Field()
    status = serpy.Field()
    user = GetUserSmallSerializer(many=False)


class GetInvoiceSerializer(GetInvoiceSmallSerializer):
    services = serpy.MethodField()
    plans = serpy.MethodField()

    def get_services(self, obj):
        service_items = ServiceItem.objects.none()
        for subscription in Subscription.objects.filter(invoice=obj):
            for service_item in subscription.services.all():
                service_items |= service_item

            # for plan in subscription.plans.all():
            #     for service_item in plan.services.all():
            #         service_items |= service_item

        return GetServiceItemSerializer(service_items.order_by('-created_at'), many=True).data

    def get_plans(self, obj):
        plans = Plan.objects.none()
        for subscription in Subscription.objects.filter(invoice=obj):
            for plan in subscription.plans.all():
                plans |= plan

        return GetPlanSerializer(plans.order_by('-created_at'), many=True).data


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


# do not use this serializer in a view
class PriceSerializer(serializers.Serializer):

    class Meta:
        model = Price
        fields = '__all__'

    def validate(self, attrs):
        return attrs

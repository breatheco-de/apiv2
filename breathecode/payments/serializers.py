import logging
import serpy
from breathecode.payments.models import Service

from breathecode.utils import serializers

logger = logging.getLogger(__name__)


class GetCohortSerializer(serpy.Serializer):
    slug = serpy.Field()


class GetMentorshipSerializer(serpy.Serializer):
    slug = serpy.Field()


class GetCohortMetadataSerializer(serpy.Serializer):
    cohort = GetCohortSerializer()


class GetMentorshipMetadataSerializer(serpy.Serializer):
    mentorship_service = GetMentorshipSerializer()


class GetServiceSerializer(serpy.Serializer):
    title = serpy.Field()
    slug = serpy.Field()
    description = serpy.Field()
    price = serpy.MethodField()
    unit_type = serpy.Field()
    # metadata = serpy.MethodField()

    # def get_price(self, obj):
    #     return obj.price if obj.price >= 0 else float('inf')

    # def get_metadata(self, obj):
    #     if obj.service_type == 'COHORT':
    #         return CohortMetadataSerializer(obj)

    #     if obj.service_type == 'MENTORSHIP':
    #         return MentorshipMetadataSerializer(obj)

    #     return None


class GetPlanSerializer(serpy.Serializer):
    title = serpy.Field()
    slug = serpy.Field()
    description = serpy.Field()
    services = serpy.MethodField()

    def get_services(self, obj):
        return obj.role.slug


class GetCurrencySerializer(serpy.Serializer):
    code = serpy.Field()
    name = serpy.Field()
    template = serpy.Field()
    regex = serpy.Field()


class GetInvoiceSerializer(serpy.Serializer):
    amount = serpy.Field()
    currency = GetCurrencySerializer(many=False)
    paid_at = serpy.Field()
    status = serpy.Field()


class GetCreditSerializer(serpy.Serializer):
    valid_until = serpy.Field()
    is_cancellable = serpy.Field()
    is_refundable = serpy.Field()
    services = GetServiceSerializer(many=True)
    invoice = GetInvoiceSerializer(many=False)

    # services = serpy.MethodField()

    # def get_services(self, obj):
    #     return obj.role.slug


class ServiceSerializer(serializers.Serializer):

    class Meta:
        model = Service
        fields = '__all__'

    def validate(self, attrs):
        return attrs

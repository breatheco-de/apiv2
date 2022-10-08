import logging
import serpy

logger = logging.getLogger(__name__)


class CohortSerializer(serpy.Serializer):
    slug = serpy.Field()


class MentorshipSerializer(serpy.Serializer):
    slug = serpy.Field()


class CohortMetadataSerializer(serpy.Serializer):
    cohort = CohortSerializer()


class MentorshipMetadataSerializer(serpy.Serializer):
    mentorship_service = MentorshipSerializer()


class ServiceSerializer(serpy.Serializer):
    """The serializer schema definition."""
    title = serpy.Field()
    slug = serpy.Field()
    description = serpy.Field()
    price = serpy.MethodField()
    unit_type = serpy.Field()
    metadata = serpy.MethodField()

    def get_price(self, obj):
        return obj.price if obj.price >= 0 else float('inf')

    def get_metadata(self, obj):
        if obj.service_type == 'COHORT':
            return CohortMetadataSerializer(obj)

        if obj.service_type == 'MENTORSHIP':
            return MentorshipMetadataSerializer(obj)

        return None


class PlanSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    title = serpy.Field()
    slug = serpy.Field()
    description = serpy.Field()
    services = serpy.MethodField()

    def get_services(self, obj):
        return obj.role.slug

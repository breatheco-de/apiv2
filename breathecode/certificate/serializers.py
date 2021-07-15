from .models import Badge, Specialty
from rest_framework import serializers
import serpy
from breathecode.admissions.serializers import SyllabusSmallSerializer, SyllabusCertificateSerializer


class ProfileSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()


class UserSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    profile = ProfileSmallSerializer(required=False, many=False)


class AcademyTinySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class AcademySmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    logo_url = serpy.Field()
    website_url = serpy.Field()


class TinyLayoutDesignSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    slug = serpy.Field()
    name = serpy.Field()
    background_url = serpy.Field()


class LayoutDesignSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    slug = serpy.Field()
    name = serpy.Field()
    is_default = serpy.Field()
    background_url = serpy.Field()


class CohortSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    syllabus = SyllabusCertificateSerializer()

class SpecialtySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    logo_url = serpy.Field()
    description = serpy.Field()

    updated_at = serpy.Field()
    created_at = serpy.Field()


class BadgeSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()


class BadgeSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    logo_url = serpy.Field()


class UserSpecialtySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    signed_by = serpy.Field()
    signed_by_role = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    user = UserSmallSerializer(many=False)
    specialty = SpecialtySerializer(many=False)
    academy = AcademySmallSerializer(many=False)
    cohort = CohortSmallSerializer(required=False, many=False)

    preview_url = serpy.Field()

    layout = TinyLayoutDesignSerializer(required=False, many=False)

    expires_at = serpy.Field()
    updated_at = serpy.Field()
    created_at = serpy.Field()

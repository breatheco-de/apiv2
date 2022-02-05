from .models import Bill
from rest_framework import serializers
import serpy


class AcademySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()
    logo_url = serpy.Field()
    website_url = serpy.Field()
    street_address = serpy.Field()


class UserSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()


class SmallFreelancerSerializer(serpy.Serializer):
    id = serpy.Field()
    user = UserSerializer()
    price_per_hour = serpy.Field()


class SmallIssueSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    title = serpy.Field()
    status = serpy.Field()
    duration_in_minutes = serpy.Field()
    duration_in_hours = serpy.Field()
    url = serpy.Field()
    github_number = serpy.Field()
    freelancer = SmallFreelancerSerializer()
    author = serpy.Field()


class BigBillSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    status = serpy.Field()
    total_duration_in_minutes = serpy.Field()
    total_duration_in_hours = serpy.Field()
    total_price = serpy.Field()
    paid_at = serpy.Field()
    created_at = serpy.Field()
    academy = AcademySerializer(required=False)

    freelancer = SmallFreelancerSerializer()
    reviewer = UserSerializer(required=False)


class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        exclude = ()

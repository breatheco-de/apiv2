from .models import Bill
from rest_framework import serializers
from breathecode.utils import serpy


class AcademySerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()
    logo_url = serpy.Field()
    website_url = serpy.Field()
    street_address = serpy.Field()


class PublicProfileSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()


class UserSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
    profile = PublicProfileSerializer(required=False)


class SmallProjectSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    title = serpy.Field()
    repository = serpy.Field()
    total_client_hourly_price = serpy.Field()


class SmallFreelancerSerializer(serpy.Serializer):
    id = serpy.Field()
    user = UserSerializer()
    price_per_hour = serpy.Field()


class TinyFreelancerMemberSerializer(serpy.Serializer):
    id = serpy.Field()
    freelancer = SmallFreelancerSerializer()
    total_cost_hourly_price = serpy.Field()
    total_client_hourly_price = serpy.Field()


class SmallFreelancerMemberSerializer(serpy.Serializer):
    id = serpy.Field()
    freelancer = SmallFreelancerSerializer()
    project = SmallProjectSerializer()
    total_cost_hourly_price = serpy.Field()
    total_client_hourly_price = serpy.Field()


class SmallIssueSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    title = serpy.Field()
    status = serpy.Field()
    status_message = serpy.Field()
    node_id = serpy.Field()
    duration_in_minutes = serpy.Field()
    duration_in_hours = serpy.Field()
    url = serpy.Field()
    github_number = serpy.Field()
    freelancer = SmallFreelancerSerializer()
    author = serpy.Field()
    included_in_bill = serpy.MethodField()

    def get_included_in_bill(self, obj):
        return (obj.status_message is None or obj.status_message == "") and (
            obj.node_id is not None and obj.node_id != ""
        )


class BigProjectSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    title = serpy.Field()
    repository = serpy.Field()
    members = serpy.MethodField()

    def get_members(self, obj):
        return TinyFreelancerMemberSerializer(obj.freelanceprojectmember_set.all(), many=True).data


class BigInvoiceSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    status = serpy.Field()
    total_duration_in_minutes = serpy.Field()
    total_duration_in_hours = serpy.Field()
    total_price = serpy.Field()
    paid_at = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()
    project = SmallProjectSerializer()
    reviewer = UserSerializer(required=False)
    issues = serpy.MethodField()

    def get_issues(self, obj):
        _issues = obj.issue_set.order_by("created_at").all()
        return SmallIssueSerializer(_issues, many=True).data


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

    issues = serpy.MethodField()

    def get_issues(self, obj):
        _issues = obj.issue_set.order_by("created_at").all()
        return SmallIssueSerializer(_issues, many=True).data


class SmallBillSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    status = serpy.Field()
    total_duration_in_hours = serpy.Field()
    total_price = serpy.Field()
    paid_at = serpy.Field()
    created_at = serpy.Field()
    freelancer = SmallFreelancerSerializer()


class BillSerializer(serializers.ModelSerializer):

    class Meta:
        model = Bill
        exclude = ("freelancer",)

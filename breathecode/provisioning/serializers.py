import re

from rest_framework import serializers

from breathecode.utils import serpy
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

from .models import ProvisioningBill, ProvisioningContainer


class AcademySerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()


class ContainerMeSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    web_url = serpy.Field()
    status = serpy.Field()
    display_name = serpy.Field()
    last_used_at = serpy.Field()
    has_unpushed_changes = serpy.Field()
    has_uncommitted_changes = serpy.Field()
    task_associated_slug = serpy.Field()


class ContainerMeBigSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    web_url = serpy.Field()
    status = serpy.Field()
    display_name = serpy.Field()
    last_used_at = serpy.Field()
    provisioned_at = serpy.Field()
    has_unpushed_changes = serpy.Field()
    has_uncommitted_changes = serpy.Field()
    branch_name = serpy.Field()
    task_associated_slug = serpy.Field()
    created_at = serpy.Field()


class GetProvisioningVendorSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()


class GetProvisioningBillSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    vendor = GetProvisioningVendorSerializer(required=False)
    total_amount = serpy.Field()
    status = serpy.Field()
    title = serpy.Field()
    status_details = serpy.Field()
    paid_at = serpy.Field()
    fee = serpy.Field()
    stripe_url = serpy.Field()
    created_at = serpy.Field()


class GetProvisioningBillSerializer(serpy.Serializer):
    id = serpy.Field()
    vendor = GetProvisioningVendorSerializer(required=False)
    total_amount = serpy.Field()
    status = serpy.Field()
    status_details = serpy.Field()
    paid_at = serpy.Field()
    fee = serpy.Field()
    stripe_url = serpy.Field()
    created_at = serpy.Field()
    title = serpy.Field()


class GetProvisioningConsumptionKindSerializer(serpy.Serializer):
    id = serpy.Field()
    product_name = serpy.Field()
    sku = serpy.Field()


class GetProvisioningUserConsumptionSerializer(serpy.Serializer):
    id = serpy.Field()
    kind = GetProvisioningConsumptionKindSerializer(required=False)
    username = serpy.Field()
    quantity = serpy.Field()
    amount = serpy.Field()
    processed_at = serpy.Field()
    status = serpy.Field()


class ProvisioningContainerSerializer(serializers.ModelSerializer):
    # slug = serializers.CharField(required=False, default=None)

    class Meta:
        model = ProvisioningContainer
        include = (
            "task_associated_slug",
            "has_uncommitted_changes",
            "branch_name",
            "destination_status",
            "destination_status_text",
        )

    def validate(self, data):

        if "slug" in data and data["slug"] is not None:

            if not re.match(r"^[-\w]+$", data["slug"]):
                raise ValidationException(
                    f'Invalid link slug {data["slug"]}, should only contain letters, numbers and slash "-"',
                    slug="invalid-slug-format",
                )

        # NOTE: this have the propertly academy but it's not defined here
        return data

    def create(self, validated_data):
        from breathecode.marketing.models import ShortLink

        return ShortLink.objects.create(**validated_data, author=self.context.get("request").user)


class ProvisioningConsumptionKindHTMLSerializer(serpy.Serializer):
    product_name = serpy.Field()
    sku = serpy.Field()


class ProvisioningConsumptionEventHTMLSerializer(serpy.Serializer):
    username = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    kind = ProvisioningConsumptionKindHTMLSerializer(required=False)


class ProvisioningUserConsumptionHTMLResumeSerializer(serpy.Serializer):
    username = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    amount = serpy.Field()
    kind = ProvisioningConsumptionKindHTMLSerializer(required=False)


class ProvisioningUserConsumptionHTMLSerializer(serpy.Serializer):
    username = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    kind = ProvisioningConsumptionKindHTMLSerializer(required=False)

    events = serpy.MethodField()

    def get_events(self, obj):
        ProvisioningConsumptionEventHTMLSerializer(obj.events, many=True).data


class ProvisioningBillHTMLSerializer(serpy.Serializer):

    id = serpy.Field()
    total_amount = serpy.Field()
    academy = AcademySerializer(required=False)
    status = serpy.Field()
    paid_at = serpy.Field()
    created_at = serpy.Field()
    title = serpy.Field()
    stripe_url = serpy.Field()


class ProvisioningBillSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProvisioningBill
        fields = ("status",)

    def validate(self, data):

        if self.instance and "status" in data and self.instance.status in ["PAID", "ERROR"]:
            status = data["status"].lower()
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en=f"You cannot change the status of this bill due to it is marked as {status}",
                    es="No puedes cambiar el estado de esta factura debido a que esta marcada " f"como {status}",
                    slug="readonly-bill-status",
                ),
                code=400,
            )

        if self.instance and "status" in data and data["status"] in ["PAID", "ERROR"]:
            status = data["status"].lower()
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en=f"You cannot set the status of this bill to {status} because this status is " "forbidden",
                    es=f"No puedes cambiar el estado de esta factura a {status} porque este estado esta " "prohibido",
                    slug="invalid-bill-status",
                ),
                code=400,
            )

        return data

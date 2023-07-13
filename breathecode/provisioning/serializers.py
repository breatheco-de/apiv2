import serpy, base64

from breathecode.utils.i18n import translation
from .models import ProvisioningBill, ProvisioningContainer, ProvisioningActivity
from django.utils import timezone
from breathecode.admissions.models import Academy
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import ValidationError
from breathecode.utils.validation_exception import ValidationException


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


class ProvisioningActivitySerializer(serpy.Serializer):
    id = serpy.Field()
    username = serpy.Field()
    registered_at = serpy.Field()
    product_name = serpy.Field()
    sku = serpy.Field()
    quantity = serpy.Field()
    unit_type = serpy.Field()
    price_per_unit = serpy.Field()
    currency_code = serpy.Field()
    multiplier = serpy.Field()
    repository_url = serpy.Field()
    processed_at = serpy.Field()
    status = serpy.Field()
    bill = serpy.MethodField()

    def get_bill(self, obj):
        return obj.bill.id if obj.bill else None


class ProvisioningContainerSerializer(serializers.ModelSerializer):
    # slug = serializers.CharField(required=False, default=None)

    class Meta:
        model = ProvisioningContainer
        include = ('task_associated_slug', 'has_uncommitted_changes', 'branch_name', 'destination_status',
                   'destination_status_text')

    def validate(self, data):

        if 'slug' in data and data['slug'] is not None:

            if not re.match('^[-\w]+$', data['slug']):
                raise ValidationException(
                    f'Invalid link slug {data["slug"]}, should only contain letters, numbers and slash "-"',
                    slug='invalid-slug-format')

        return {**data, 'academy': academy}

    def create(self, validated_data):

        return ShortLink.objects.create(**validated_data, author=self.context.get('request').user)


class GETProvisioningBillSerializer(serpy.Serializer):
    total_amount = serpy.Field()
    academy = AcademySerializer(required=False)
    status = serpy.Field()
    paid_at = serpy.Field()
    stripe_url = serpy.Field()
    activities = serpy.MethodField()

    def get_activities(self, obj):
        activities = ProvisioningActivity.objects.filter(bill=obj.id)
        activities_filtered = {}
        for activity in activities:
            username = activity.username
            quantity = activity.quantity
            if username in activities_filtered:
                activities_filtered[username]['quantity'] += quantity
            else:
                activities_filtered[username] = {
                    'username': activity.username,
                    'product_name': activity.product_name,
                    'status': activity.status,
                    'status_text': activity.status_text,
                    'price_per_unit': activity.price_per_unit,
                    'quantity': quantity,
                    'multiplier': activity.multiplier
                }
        bill_activities = []
        for activity in activities_filtered.values():
            bill_activities.append(activity)
        return bill_activities


class ProvisioningBillSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProvisioningBill
        fields = ('status', )

    def validate(self, data):

        if self.instance and 'status' in data and self.instance.status in ['PAID', 'ERROR']:
            status = data['status'].lower()
            raise ValidationException(translation(
                self.context['lang'],
                en=f'You cannot change the status of this bill due to it is marked as {status}',
                es='No puedes cambiar el estado de esta factura debido a que esta marcada '
                f'como {status}',
                slug='readonly-bill-status'),
                                      code=400)

        if self.instance and 'status' in data and data['status'] in ['PAID', 'ERROR']:
            status = data['status'].lower()
            raise ValidationException(translation(
                self.context['lang'],
                en=f'You cannot set the status of this bill to {status} because this status is '
                'forbidden',
                es=f'No puedes cambiar el estado de esta factura a {status} porque este estado esta '
                'prohibido',
                slug='invalid-bill-status'),
                                      code=400)

        return data

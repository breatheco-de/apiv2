import math
import serpy

from breathecode.utils.i18n import translation
from .models import ProvisioningBill, ProvisioningConsumptionEvent, ProvisioningContainer, ProvisioningUserConsumption

from rest_framework import serializers
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
    kind = ProvisioningConsumptionKindHTMLSerializer(required=False)

    price_description = serpy.MethodField()

    def get_price_description(self, obj):
        # import sum function from django
        from django.db.models import Sum

        event_length = ProvisioningConsumptionEvent.objects.filter().count()
        event_pages = math.ceil(event_length / 100)
        quantity = 0
        price = 0
        page = 0
        prices = []

        while page < event_pages:
            events = ProvisioningConsumptionEvent.objects.filter().order_by('id')[page * 100:(page * 100) +
                                                                                  100]
            for event in events:
                quantity += event.quantity
                p = event.quantity * event.price.price_per_unit * event.price.multiplier
                price += p

                prices.append({
                    'price': p,
                    'price_per_unit': event.price.price_per_unit,
                    'quantity': event.quantity
                })

            page += 1

        resume = ''

        for p in prices:
            resume += f'{p["quantity"]} x {p["price_per_unit"]} = {p["price"]}\n'

        return quantity, price, resume


class ProvisioningUserConsumptionHTMLSerializer(serpy.Serializer):
    username = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    kind = ProvisioningConsumptionKindHTMLSerializer(required=False)

    events = serpy.MethodField()

    def get_events(self, obj):
        ProvisioningConsumptionEventHTMLSerializer(obj.events, many=True).data


class ProvisioningBillHTMLSerializer(serpy.Serializer):

    total_amount = serpy.Field()
    academy = AcademySerializer(required=False)
    status = serpy.Field()
    paid_at = serpy.Field()
    stripe_url = serpy.Field()


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

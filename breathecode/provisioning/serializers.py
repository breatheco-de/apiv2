import serpy, base64
from .models import ProvisioningContainer
from django.utils import timezone
from breathecode.admissions.models import Academy
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import ValidationError
from breathecode.utils.validation_exception import ValidationException


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

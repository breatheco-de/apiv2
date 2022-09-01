from django.contrib.auth.models import User
from django.conf import settings
from .models import Device, Hook
from breathecode.admissions.models import Academy
from breathecode.utils.validation_exception import ValidationException
from rest_framework import serializers
import serpy


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class HookSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    user = UserSerializer()
    target = serpy.Field()
    event = serpy.Field()


class DeviceSerializer(serpy.Serializer):
    id = serpy.Field()
    registration_id = serpy.Field()
    created_at = serpy.Field()


class HookSerializer(serializers.ModelSerializer):

    def validate(self, data):

        if data['event'] not in settings.HOOK_EVENTS:
            err_msg = 'Unexpected event {}'.format(data['event'])
            raise ValidationException(err_msg, slug='invalid-event')

        # superadmins can subscribe to any hook without needed an academy token
        if not self.context['request'].user.is_superuser:
            academy = Academy.objects.filter(slug=self.context['request'].user.username).first()
            if academy is None:
                raise ValidationException('No valid academy token found', slug='invalid-academy-token')

        data['user'] = self.context['request'].user

        return super().validate(data)

    class Meta:
        model = Hook
        fields = '__all__'
        read_only_fields = ('user', )

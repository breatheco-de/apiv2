from .models import Device
from rest_framework import serializers
import serpy


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class DeviceSerializer(serpy.Serializer):
    id = serpy.Field()
    registration_id = serpy.Field()
    created_at = serpy.Field()

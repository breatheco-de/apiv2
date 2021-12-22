from .models import Platform
from rest_framework import serializers
import serpy


class GetPlatformSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()

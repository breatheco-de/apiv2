from .models import Asset
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import serpy
from django.utils import timezone

class AssetSerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    asset_type = serpy.Field()
    visibility = serpy.Field()
    url = serpy.Field()
    gitpod = serpy.Field()
    preview = serpy.Field()

class AssetBigSerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    description = serpy.Field()
    gitpod = serpy.Field()
    visibility = serpy.Field()
    asset_type = serpy.Field()
    visibility = serpy.Field()
    url = serpy.Field()
    gitpod = serpy.Field()
    preview = serpy.Field()
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
    readme_url = serpy.Field()
    difficulty = serpy.Field()
    duration = serpy.Field()
    status = serpy.Field()
    graded = serpy.Field()
    gitpod = serpy.Field()
    preview = serpy.Field()

    translations = serpy.MethodField()
    technologies = serpy.MethodField()

    def get_translations(self,obj):
        _s = map(lambda t: t.slug, obj.translations.all())
        return _s
    def get_technologies(self,obj):
        _s = map(lambda t: t.slug, obj.technologies.all())
        return _s

class AssetBigSerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    description = serpy.Field()
    gitpod = serpy.Field()
    visibility = serpy.Field()
    difficulty = serpy.Field()
    with_video = serpy.Field()
    duration = serpy.Field()
    readme_url = serpy.Field()
    readme = serpy.Field()
    asset_type = serpy.Field()
    visibility = serpy.Field()
    url = serpy.Field()
    gitpod = serpy.Field()
    preview = serpy.Field()

from .models import Asset
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import serpy
from django.utils import timezone


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class AssetSerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
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
    readme_url = serpy.Field()
    solution_video_url = serpy.Field()
    intro_video_url = serpy.Field()

    translations = serpy.MethodField()
    technologies = serpy.MethodField()

    def get_translations(self, obj):
        _s = map(lambda t: t.slug, obj.translations.all())
        return _s

    def get_technologies(self, obj):
        _s = map(lambda t: t.slug, obj.technologies.all())
        return _s


class AssetMidSerializer(AssetSerializer):

    solution_url = serpy.Field()
    readme = serpy.Field()

    interactive = serpy.Field()
    with_solutions = serpy.Field()
    with_video = serpy.Field()


class AssetBigSerializer(AssetMidSerializer):

    description = serpy.Field()

    status_text = serpy.Field()

    author = UserSerializer(required=False)

    created_at = serpy.Field()
    updated_at = serpy.Field()


class AssetTechnologySerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()

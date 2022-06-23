from .models import Asset, AssetAlias
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import serpy
from breathecode.utils.validation_exception import ValidationException
from django.utils import timezone


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class AcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()


class AssetCategorySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()


class KeywordClusterSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()


class AssetSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    category = AssetCategorySmallSerializer(required=False)
    asset_type = serpy.Field()
    visibility = serpy.Field()
    url = serpy.Field()
    readme_url = serpy.Field()
    difficulty = serpy.Field()
    duration = serpy.Field()
    description = serpy.Field()
    status = serpy.Field()
    graded = serpy.Field()
    gitpod = serpy.Field()
    preview = serpy.Field()
    external = serpy.Field()
    solution_video_url = serpy.Field()
    intro_video_url = serpy.Field()

    translations = serpy.MethodField()
    technologies = serpy.MethodField()
    seo_keywords = serpy.MethodField()

    def get_translations(self, obj):
        result = {}
        for t in obj.all_translations.all():
            result[t.lang] = t.slug
        return result

    def get_technologies(self, obj):
        _s = list(map(lambda t: t.slug, obj.technologies.all()))
        return _s

    def get_seo_keywords(self, obj):
        _s = list(map(lambda t: t.slug, obj.seo_keywords.all()))
        return _s


class AssetMidSerializer(AssetSerializer):

    solution_url = serpy.Field()
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


class AssetCategorySerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    academy = AcademySmallSerializer()


class KeywordClusterSerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    academy = AcademySmallSerializer()
    lang = serpy.Field()


class AssetKeywordSerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    academy = AcademySmallSerializer()
    cluster = KeywordClusterSmallSerializer()


class PostAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        exclude = ()

    def validate(self, data):

        validated_data = super().validate(data)

        alias = AssetAlias.objects.filter(slug=validated_data['slug']).first()
        if alias is not None:
            raise ValidationException('Asset alias already exists with this slug')

        return validated_data

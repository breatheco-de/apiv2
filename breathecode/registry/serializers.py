from .models import Asset, AssetAlias
from breathecode.authenticate.models import ProfileAcademy
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import ValidationError
import serpy
from breathecode.utils.validation_exception import ValidationException
from django.utils import timezone


class ProfileSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()
    github_username = serpy.Field()


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    profile = ProfileSerializer(required=False)


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


class AcademyAssetSerializer(AssetSerializer):
    test_status = serpy.Field()
    last_test_at = serpy.Field()
    sync_status = serpy.Field()
    last_synch_at = serpy.Field()
    status_text = serpy.Field()
    published_at = serpy.Field()

    author = UserSerializer(required=False)
    owner = UserSerializer(required=False)


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


class AssetPUTSerializer(serializers.ModelSerializer):
    url = serializers.CharField(required=False)
    asset_type = serializers.CharField(required=False)

    # url = serializers.CharField(required=False)
    # url = serializers.CharField(required=False)

    class Meta:
        model = Asset
        exclude = ('technologies', )

    def validate(self, data):

        academy_id = self.context.get('academy_id')
        session_user = self.context.get('request').user
        member = ProfileAcademy.objects.filter(user=session_user, academy__id=academy_id).first()
        if member is None:
            raise ValidationException(f"You don't belong to the academy {academy_id} owner of this asset",
                                      status.HTTP_400_BAD_REQUEST)

        if member.role.slug == 'content_writer':
            for key in data:
                if key != 'status' and data[key] != getattr(self.instance, key):
                    raise ValidationException(f'You are only allowed to change the status of this asset',
                                              status.HTTP_400_BAD_REQUEST)
            if 'status' in data and data['status'] not in ['DRAFT', 'WRITING', 'UNASSIGNED']:
                raise ValidationException(f'You can only set the status to draft, writing or unassigned',
                                          status.HTTP_400_BAD_REQUEST)

            if self.instance.author is None and data['status'] != 'UNASSIGNED':
                data['author'] = session_user
            elif self.instance.author.id != session_user.id:
                raise ValidationException(f'You can only update card assigned to yourself',
                                          status.HTTP_400_BAD_REQUEST)
            elif data['status'] == 'UNASSIGNED':
                data['author'] = None

        validated_data = super().validate(data)
        return validated_data

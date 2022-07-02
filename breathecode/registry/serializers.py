from .models import Asset, AssetAlias, AssetComment, AssetKeyword, AssetTechnology
from django.db.models import Count
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


class SmallAsset(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()


class AcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()


class AssetCategorySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()


class KeywordClusterSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()


class AcademyCommentSerializer(serpy.Serializer):
    id = serpy.Field()
    text = serpy.Field()
    asset = SmallAsset()
    resolved = serpy.Field()
    author = UserSerializer()
    created_at = serpy.Field()


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
        _s = list(map(lambda t: t.slug, obj.technologies.filter(parent__isnull=True)))
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
    owner = UserSerializer(required=False)

    test_status = serpy.Field()
    last_test_at = serpy.Field()
    sync_status = serpy.Field()
    last_synch_at = serpy.Field()
    status_text = serpy.Field()
    published_at = serpy.Field()

    created_at = serpy.Field()
    updated_at = serpy.Field()


class ParentAssetTechnologySerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    description = serpy.Field()
    icon_url = serpy.Field()


class AssetTechnologySerializer(ParentAssetTechnologySerializer):
    parent = ParentAssetTechnologySerializer(required=False)


class AssetBigTechnologySerializer(AssetTechnologySerializer):

    assets = serpy.MethodField()
    alias = serpy.MethodField()

    def get_assets(self, obj):
        assets = Asset.objects.filter(technologies__id=obj.id)
        return list(map(lambda t: t.slug, assets))

    def get_alias(self, obj):
        techs = AssetTechnology.objects.filter(parent=obj.id)
        return list(map(lambda t: t.slug, techs))


class AssetCategorySerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    academy = AcademySmallSerializer()


class _Keyword(serpy.Serializer):
    slug = serpy.Field()
    published_assets = serpy.MethodField()

    def get_published_assets(self, obj):
        return list(map(lambda t: t.slug, obj.asset_set.filter(status='PUBLISHED')))


class KeywordClusterSerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    academy = AcademySmallSerializer()
    lang = serpy.Field()

    total_articles = serpy.MethodField()
    keywords = serpy.MethodField()

    def get_keywords(self, obj):
        kws = AssetKeyword.objects.filter(cluster__id=obj.id)
        return _Keyword(kws, many=True).data

    def get_total_articles(self, obj):
        return Asset.objects.filter(seo_keywords__cluster__id=obj.id).count()


class AssetKeywordSerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    academy = AcademySmallSerializer()
    cluster = KeywordClusterSmallSerializer()


class TechSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetTechnology


class PostAssetSerializer(serializers.ModelSerializer):
    technologies = TechSerializer(many=True, required=False)

    class Meta:
        model = Asset
        exclude = ()

    def validate(self, data):

        validated_data = super().validate(data)

        alias = AssetAlias.objects.filter(slug=validated_data['slug']).first()
        if alias is not None:
            raise ValidationException('Asset alias already exists with this slug')

        return validated_data


class TechnolgyPUTSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetTechnology
        exclude = ('slug', )


class PostAssetCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetComment
        exclude = ()


class PutAssetCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetComment
        exclude = ('text', 'asset', 'author')

    def validate(self, data):

        validated_data = super().validate(data)

        academy_id = self.context.get('academy_id')
        session_user = self.context.get('request').user

        if self.instance.author is not None and self.instance.author.id != session_user.id:
            raise ValidationException('Only the comment author can mark this comment as resolved')

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

        if 'status' in data and data['status'] == 'PUBLISHED':
            if self.instance.test_status != 'Ok':
                raise ValidationException(f'This asset has to pass tests successfully before publishing',
                                          status.HTTP_400_BAD_REQUEST)

        validated_data = super().validate(data)
        return validated_data

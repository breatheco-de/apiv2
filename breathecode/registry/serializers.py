import serpy, base64
from .models import Asset, AssetAlias, AssetComment, AssetKeyword, AssetTechnology, KeywordCluster, AssetCategory
from django.db.models import Count
from breathecode.authenticate.models import ProfileAcademy
from breathecode.admissions.models import Academy
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import ValidationError
from breathecode.utils.validation_exception import ValidationException
from django.utils import timezone


class ProfileSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()
    github_username = serpy.Field()


class KeywordSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()


class KeywordClusterSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()


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


class AssetKeywordSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    cluster = KeywordClusterSmallSerializer(required=False)


class AssetKeywordBigSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    cluster = KeywordClusterSmallSerializer(required=False)

    published_assets = serpy.MethodField()

    def get_published_assets(self, obj):
        return list(map(lambda t: t.slug, obj.asset_set.filter(status='PUBLISHED')))


class AcademyCommentSerializer(serpy.Serializer):
    id = serpy.Field()
    text = serpy.Field()
    asset = SmallAsset()
    resolved = serpy.Field()
    delivered = serpy.Field()
    author = UserSerializer(required=False)
    owner = UserSerializer(required=False)
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

    requirements = serpy.Field()

    last_seo_scan_at = serpy.Field()
    seo_json_status = serpy.Field()
    optimization_rating = serpy.Field()

    cleaning_status = serpy.Field()
    cleaning_status_details = serpy.Field()
    last_cleaning_at = serpy.Field()

    author = UserSerializer(required=False)
    owner = UserSerializer(required=False)

    def get_seo_keywords(self, obj):
        return list(map(lambda t: AssetKeywordSerializer(t).data, obj.seo_keywords.all()))


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

    academy = AcademySmallSerializer(required=False)


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
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    academy = AcademySmallSerializer()


class _Keyword(serpy.Serializer):
    slug = serpy.Field()
    published_assets = serpy.MethodField()

    def get_published_assets(self, obj):
        return list(map(lambda t: t.slug, obj.asset_set.filter(status='PUBLISHED')))


class KeywordClusterBigSerializer(serpy.Serializer):
    id = serpy.Field()
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


class TechSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetTechnology


class PostAssetSerializer(serializers.ModelSerializer):
    technologies = serializers.ListField(required=False)

    class Meta:
        model = Asset
        exclude = ('academy', )

    def validate(self, data):

        validated_data = super().validate(data)

        academy_id = self.context['academy']
        validated_data['academy'] = Academy.objects.filter(id=academy_id).first()

        alias = AssetAlias.objects.filter(slug=validated_data['slug']).first()
        if alias is not None:
            raise ValidationException('Asset alias already exists with this slug')

        if 'readme' in validated_data:
            raise ValidationException(
                'Property readme is read only, please update property readme_raw instead')

        return validated_data

    def create(self, validated_data):
        academy_id = self.context['academy']
        academy = Academy.objects.filter(id=academy_id).first()

        readme_raw = None
        if 'readme_raw' in validated_data:
            readme_raw = validated_data['readme_raw']

        return super(PostAssetSerializer, self).create({
            **validated_data, 'academy': academy,
            'readme_raw': readme_raw
        })


class PostKeywordClusterSerializer(serializers.ModelSerializer):

    class Meta:
        model = KeywordCluster
        exclude = ('academy', )

    def create(self, validated_data):
        academy_id = self.context['academy']
        academy = Academy.objects.filter(id=academy_id).first()

        return super(PostKeywordClusterSerializer, self).create({
            **validated_data,
            'academy': academy,
        })

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class PostKeywordSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetKeyword
        exclude = ('academy', )

    def create(self, validated_data):
        academy_id = self.context['academy']
        academy = Academy.objects.filter(id=academy_id).first()

        return super(PostKeywordSerializer, self).create({
            **validated_data,
            'academy': academy,
        })


class PUTKeywordSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False)
    title = serializers.CharField(required=False)
    lang = serializers.CharField(required=False)

    class Meta:
        model = AssetKeyword
        exclude = ('academy', )

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class PUTCategorySerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False)
    title = serializers.CharField(required=False)
    lang = serializers.CharField(required=False)

    class Meta:
        model = AssetCategory
        exclude = ('academy', )

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class POSTCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetCategory
        exclude = ('academy', )

    def create(self, validated_data):
        academy_id = self.context['academy']
        academy = Academy.objects.filter(id=academy_id).first()

        return super().create({
            **validated_data,
            'academy': academy,
        })


class TechnologyPUTSerializer(serializers.ModelSerializer):
    parent = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = AssetTechnology
        exclude = ('slug', )

    def validate(self, data):
        validated_data = {**data}

        if 'parent' in data and data['parent'] is not None:
            parent = None
            if isinstance(data['parent'], int) or data['parent'].isnumeric():
                parent = AssetTechnology.objects.filter(id=data['parent']).first()
            else:
                parent = AssetTechnology.objects.filter(slug=data['parent']).first()

            if parent.parent is not None:
                raise ValidationException(
                    f'The technology parent you are trying to set {parent.slug}, its a child of another technology, only technologies without parent can be set as parent'
                )

            if parent is None:
                raise ValidationException(f'Parent with slug or id {data["parent"]} not found')

            # if parent.id == self.instance.id:
            #     raise ValidationException(f'Technology cannot be a parent of itself')

            validated_data['parent'] = parent

        return validated_data

    def update(self, instance, validated_data):
        if 'parent' in validated_data and validated_data['parent'] is None:
            instance.parent = validated_data.pop('parent')
            instance.save()

        return super().update(instance, validated_data)


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
            if 'resolved' in data and data['resolved'] != self.instance.resolved:
                raise ValidationException('Only the comment/issue author can update the resolved property')

        return validated_data


class AssetPUTSerializer(serializers.ModelSerializer):
    url = serializers.CharField(required=False)
    technologies = serializers.ListField(required=False)
    slug = serializers.CharField(required=False)
    asset_type = serializers.CharField(required=False)

    class Meta:
        model = Asset
        exclude = ('academy', )

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
            if self.instance.test_status != 'OK':
                raise ValidationException(f'This asset has to pass tests successfully before publishing',
                                          status.HTTP_400_BAD_REQUEST)

        validated_data = super().validate(data)
        return validated_data

from django.utils import timezone
from rest_framework import serializers, status
from slugify import slugify

from breathecode.admissions.models import Academy
from breathecode.authenticate.models import ProfileAcademy
from breathecode.utils import serpy
from capyc.rest_framework.exceptions import ValidationException

from .models import (
    Asset,
    AssetAlias,
    AssetCategory,
    AssetComment,
    AssetKeyword,
    AssetTechnology,
    ContentVariable,
    KeywordCluster,
)


class ProfileSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()
    github_username = serpy.Field()


class SEOReportSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    report_type = serpy.Field()
    status = serpy.Field()
    log = serpy.Field()
    rating = serpy.Field()
    how_to_fix = serpy.Field()
    created_at = serpy.Field()


class OriginalityScanSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    success = serpy.Field()
    score_original = serpy.Field()
    score_ai = serpy.Field()
    credits_used = serpy.Field()
    content = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class VariableSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    key = serpy.Field()
    value = serpy.Field()
    default_value = serpy.Field()
    lang = serpy.Field()


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


class AssetAliasSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    slug = serpy.Field()
    asset = SmallAsset()


class AssetImageSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    bucket_url = serpy.Field()
    original_url = serpy.Field()
    download_details = serpy.Field()
    download_status = serpy.Field()

    assets = serpy.MethodField()

    def get_assets(self, obj):
        return AssetSmallSerializer(obj.assets.all(), many=True).data


class AssetCategorySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()


class AssetTinySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()


class AssetSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    asset_type = serpy.Field()
    status = serpy.Field()
    published_at = serpy.Field()
    category = AssetCategorySmallSerializer(required=False)

    technologies = serpy.MethodField()

    def get_technologies(self, obj):
        techs = AssetTechnology.objects.filter(id__in=obj.technologies.filter(is_deprecated=False))
        return ParentAssetTechnologySerializer(techs, many=True).data


class AcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()


class AssessmentSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()


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

    all_assets = serpy.MethodField()

    def get_all_assets(self, obj):
        return AssetSmallSerializer(obj.asset_set.all(), many=True).data


class AcademyCommentSerializer(serpy.Serializer):
    id = serpy.Field()
    text = serpy.Field()
    asset = SmallAsset()
    resolved = serpy.Field()
    delivered = serpy.Field()
    author = UserSerializer(required=False)
    owner = UserSerializer(required=False)
    created_at = serpy.Field()


class AssetHookSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    academy = AcademySmallSerializer(required=False)
    category = AssetCategorySmallSerializer(required=False)
    asset_type = serpy.Field()
    visibility = serpy.Field()
    url = serpy.Field()
    readme_url = serpy.Field()
    readme = serpy.Field()
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
    published_at = serpy.Field()

    technologies = serpy.MethodField()
    seo_keywords = serpy.MethodField()

    def get_technologies(self, obj):
        _s = list(map(lambda t: t.slug, obj.technologies.filter(parent__isnull=True).order_by("sort_priority")))
        return ",".join(_s)

    def get_seo_keywords(self, obj):
        _s = list(map(lambda t: t.slug, obj.seo_keywords.all()))
        return ",".join(_s)


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
    solution_url = serpy.Field()
    intro_video_url = serpy.Field()
    published_at = serpy.Field()

    translations = serpy.MethodField()
    technologies = serpy.MethodField()
    seo_keywords = serpy.MethodField()

    assets_related = serpy.MethodField()

    def get_assets_related(self, obj):
        _assets_related = [AssetSmallSerializer(asset).data for asset in obj.assets_related.all()]
        return _assets_related

    def get_translations(self, obj):
        result = {}
        for t in obj.all_translations.all():
            result[t.lang] = t.slug
        return result

    def get_technologies(self, obj):
        _s = list(map(lambda t: t.slug, obj.technologies.filter(parent__isnull=True).order_by("sort_priority")))
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
    readme_updated_at = serpy.Field()
    authors_username = serpy.Field()

    requirements = serpy.Field()

    is_seo_tracked = serpy.Field()
    last_seo_scan_at = serpy.Field()
    seo_json_status = serpy.Field()
    optimization_rating = serpy.Field()

    cleaning_status = serpy.Field()
    cleaning_status_details = serpy.Field()
    last_cleaning_at = serpy.Field()

    assessment = AssessmentSmallSerializer(required=False)

    author = UserSerializer(required=False)
    owner = UserSerializer(required=False)

    created_at = serpy.Field()
    updated_at = serpy.Field()
    published_at = serpy.Field()

    clusters = serpy.MethodField()
    previous_versions = serpy.MethodField()

    def get_clusters(self, obj):
        return [k.cluster.slug for k in obj.seo_keywords.all() if k.cluster is not None]

    def get_seo_keywords(self, obj):
        return list(map(lambda t: AssetKeywordSerializer(t).data, obj.seo_keywords.all()))

    def get_previous_versions(self, obj):

        prev_versions = []
        _aux = obj
        try:
            while _aux.previous_version is not None:
                prev_versions.append(_aux.previous_version)
                _aux = _aux.previous_version
        except Exception:
            pass

        serializer = AssetTinySerializer(prev_versions, many=True)
        return serializer.data


class AssetMidSerializer(AssetSerializer):

    solution_url = serpy.Field()
    interactive = serpy.Field()
    with_solutions = serpy.Field()
    with_video = serpy.Field()
    updated_at = serpy.Field()


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

    enable_table_of_content = serpy.Field()

    delivery_instructions = serpy.Field()
    delivery_formats = serpy.Field()
    delivery_regex_url = serpy.Field()

    academy = AcademySmallSerializer(required=False)

    cluster = KeywordClusterSmallSerializer(required=False)

    assets_related = serpy.MethodField()
    superseded_by = AssetTinySerializer(required=False)

    def get_assets_related(self, obj):
        _assets_related = [AssetSmallSerializer(asset).data for asset in obj.assets_related.filter(lang=obj.lang)]
        return _assets_related


class ParentAssetTechnologySerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    description = serpy.Field()
    icon_url = serpy.Field()
    is_deprecated = serpy.Field()
    visibility = serpy.Field()


class AssetBigAndTechnologySerializer(AssetBigSerializer):

    technologies = serpy.MethodField()

    def get_technologies(self, obj):
        techs = AssetTechnology.objects.filter(id__in=obj.technologies.filter(is_deprecated=False))
        return ParentAssetTechnologySerializer(techs, many=True).data


# Remove anything not published or visible, this serializer will be using for public API
# the admin.4geeks.com will use another one
class AssetBigAndTechnologyPublishedSerializer(AssetBigSerializer):

    assessment = AssessmentSmallSerializer(required=False)

    technologies = serpy.MethodField()
    translations = serpy.MethodField()

    def get_translations(self, obj):
        result = {}
        for t in obj.all_translations.filter(status="PUBLISHED"):
            result[t.lang] = t.slug
        return result

    def get_technologies(self, obj):
        techs = AssetTechnology.objects.filter(
            id__in=obj.technologies.filter(visibility__in=["PUBLIC", "UNLISTED"], is_deprecated=False)
        )
        return ParentAssetTechnologySerializer(techs, many=True).data


class AssetAndTechnologySerializer(AssetSerializer):

    technologies = serpy.MethodField()

    def get_technologies(self, obj):
        techs = AssetTechnology.objects.filter(
            id__in=obj.technologies.filter(visibility__in=["PUBLIC", "UNLISTED"], is_deprecated=False)
        )
        return ParentAssetTechnologySerializer(techs, many=True).data


class AssetTechnologySerializer(ParentAssetTechnologySerializer):
    parent = ParentAssetTechnologySerializer(required=False)
    lang = serpy.Field(required=False)


class AssetBigTechnologySerializer(AssetTechnologySerializer):

    assets = serpy.MethodField()
    alias = serpy.MethodField()
    sort_priority = serpy.Field()

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
    id = serpy.Field()
    slug = serpy.Field()
    all_assets = serpy.MethodField()

    def get_all_assets(self, obj):
        return AssetSmallSerializer(obj.asset_set.all(), many=True).data


class KeywordClusterMidSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    academy = AcademySmallSerializer()
    lang = serpy.Field()
    landing_page_url = serpy.Field()

    total_articles = serpy.MethodField()
    keywords = serpy.MethodField()

    def get_keywords(self, obj):
        kws = AssetKeyword.objects.filter(cluster__id=obj.id)
        return _Keyword(kws, many=True).data

    def get_total_articles(self, obj):
        return Asset.objects.filter(seo_keywords__cluster__id=obj.id).count()


class KeywordClusterBigSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    academy = AcademySmallSerializer()
    lang = serpy.Field()
    landing_page_url = serpy.Field()
    visibility = serpy.Field()
    is_deprecated = serpy.Field()
    is_important = serpy.Field()
    is_urgent = serpy.Field()
    internal_description = serpy.Field()
    optimization_rating = serpy.Field()

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
        exclude = ("academy",)

    def validate(self, data):

        validated_data = super().validate(data)

        if "lang" not in validated_data or validated_data["lang"] is None:
            raise ValidationException("Asset is missing a language", slug="no-language")

        if "category" not in data or data["category"] is None:
            if "all_translations" not in validated_data or len(validated_data["all_translations"]) == 0:
                raise ValidationException(
                    "No category was specified and we could not retrieve it from any translation", slug="no-category"
                )

            asset_translation = Asset.objects.filter(slug=validated_data["all_translations"][0]).first()
            if asset_translation is None or asset_translation.category is None:
                raise ValidationException(
                    "No category was specified and we could not retrieve it from any translation", slug="no-category"
                )

            category_translation = asset_translation.category.all_translations.filter(
                lang=validated_data["lang"]
            ).first()
            if category_translation is None:
                raise ValidationException(
                    f"No category was specified and translation's categories don't have language: {validated_data['lang']}"
                )

            validated_data["category"] = category_translation

        academy_id = self.context["academy"]
        validated_data["academy"] = Academy.objects.filter(id=academy_id).first()

        alias = AssetAlias.objects.filter(slug=validated_data["slug"]).first()
        if alias is not None:
            raise ValidationException("Asset alias already exists with this slug")

        if "readme" in validated_data:
            raise ValidationException("Property readme is read only, please update property readme_raw instead")

        return validated_data

    def create(self, validated_data):
        academy_id = self.context["academy"]
        academy = Academy.objects.filter(id=academy_id).first()

        readme_raw = None
        if "readme_raw" in validated_data:
            readme_raw = validated_data["readme_raw"]

        try:
            return super(PostAssetSerializer, self).create(
                {**validated_data, "academy": academy, "readme_raw": readme_raw}
            )
        except Exception as e:

            raise ValidationException(e.message_dict, 400)


class PostKeywordClusterSerializer(serializers.ModelSerializer):

    class Meta:
        model = KeywordCluster
        exclude = ("academy",)

    def validate(self, data):

        validated_data = super().validate(data)

        if "landing_page_url" in validated_data:
            if "http" not in validated_data["landing_page_url"]:
                raise ValidationException(
                    "Please make your topic cluster landing page url is an absolute url that points to your page, this is how we know your page domain"
                )

        return validated_data

    def create(self, validated_data):
        academy_id = self.context["academy"]
        academy = Academy.objects.filter(id=academy_id).first()

        return super(PostKeywordClusterSerializer, self).create(
            {
                **validated_data,
                "academy": academy,
            }
        )

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class PostKeywordSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetKeyword
        exclude = ("academy",)

    def create(self, validated_data):
        academy_id = self.context["academy"]
        academy = Academy.objects.filter(id=academy_id).first()

        return super(PostKeywordSerializer, self).create(
            {
                **validated_data,
                "academy": academy,
            }
        )


class PUTKeywordSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False)
    title = serializers.CharField(required=False)
    lang = serializers.CharField(required=False)

    class Meta:
        model = AssetKeyword
        exclude = ("academy",)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class PUTCategorySerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False)
    title = serializers.CharField(required=False)
    lang = serializers.CharField(required=False)

    class Meta:
        model = AssetCategory
        exclude = ("academy",)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class POSTCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetCategory
        exclude = ("academy",)

    def create(self, validated_data):
        academy_id = self.context["academy"]
        academy = Academy.objects.filter(id=academy_id).first()

        return super().create(
            {
                **validated_data,
                "academy": academy,
            }
        )


class TechnologyPUTSerializer(serializers.ModelSerializer):
    parent = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = AssetTechnology
        exclude = ("slug",)

    def validate(self, data):
        validated_data = {**data}

        if "parent" in data and data["parent"] is not None:
            parent = None
            if isinstance(data["parent"], int) or data["parent"].isnumeric():
                parent = AssetTechnology.objects.filter(id=data["parent"]).first()
            else:
                parent = AssetTechnology.objects.filter(slug=data["parent"]).first()

            if parent.parent is not None:
                raise ValidationException(
                    f"The technology parent you are trying to set {parent.slug}, its a child of another technology, only technologies without parent can be set as parent"
                )

            if parent is None:
                raise ValidationException(f'Parent with slug or id {data["parent"]} not found')

            # if parent.id == self.instance.id:
            #     raise ValidationException(f'Technology cannot be a parent of itself')

            validated_data["parent"] = parent

        return validated_data

    def update(self, instance, validated_data):
        if "parent" in validated_data and validated_data["parent"] is None:
            instance.parent = validated_data.pop("parent")
            instance.save()

        return super().update(instance, validated_data)


class PostAssetCommentSerializer(serializers.ModelSerializer):
    asset = serializers.CharField(required=True)

    class Meta:
        model = AssetComment
        exclude = ()

    def validate(self, data):

        academy_id = self.context.get("academy")
        asset = None
        if "asset" in data:
            if data["asset"].isnumeric():
                asset = Asset.objects.filter(id=data["asset"], academy__id=academy_id).first()
            elif data["asset"] != "":
                asset = Asset.objects.filter(slug=data["asset"], academy__id=academy_id).first()

        if asset is None:
            raise ValidationException(f'Asset {data["asset"]} not found for academy {academy_id}')

        return super().validate({**data, "asset": asset})


class PutAssetCommentSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetComment
        exclude = ("text", "asset", "author")

    def validate(self, data):

        validated_data = super().validate(data)
        session_user = self.context.get("request").user

        if self.instance.owner is not None and self.instance.owner.id == session_user.id:
            if "resolved" in data and data["resolved"] != self.instance.resolved:
                raise ValidationException("You cannot update the resolved property if you are the Asset Comment owner")

        return validated_data


class AssetListSerializer(serializers.ListSerializer):

    def update(self, instances, validated_data):

        instance_hash = {index: instance for index, instance in enumerate(instances)}

        result = [self.child.update(instance_hash[index], attrs) for index, attrs in enumerate(validated_data)]

        return result


class VariableSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContentVariable
        exclude = ("academy",)


class AssetPUTSerializer(serializers.ModelSerializer):
    url = serializers.CharField(required=False)
    technologies = serializers.ListField(required=False)
    slug = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    visibility = serializers.CharField(required=False)
    asset_type = serializers.CharField(required=False)

    class Meta:
        model = Asset
        exclude = ("academy",)
        list_serializer_class = AssetListSerializer

    def validate(self, data):

        academy_id = self.context.get("academy_id")
        session_user = self.context.get("request").user
        member = ProfileAcademy.objects.filter(user=session_user, academy__id=academy_id).first()
        if member is None:
            raise ValidationException(
                f"You don't belong to the academy {academy_id} owner of this asset", status.HTTP_400_BAD_REQUEST
            )

        if member.role.slug == "content_writer":
            for key in data:
                if key != "status" and data[key] != getattr(self.instance, key):
                    raise ValidationException(
                        "You are only allowed to change the status of this asset", status.HTTP_400_BAD_REQUEST
                    )
            if "status" in data and data["status"] not in ["DRAFT", "WRITING", "NOT_STARTED", "OPTIMIZED", "PLANNING"]:
                raise ValidationException(
                    "You can only set the status to not started, draft, writing, optimized, or planning",
                    status.HTTP_400_BAD_REQUEST,
                )

            if self.instance.author is None and data["status"] != "NOT_STARTED":
                data["author"] = session_user
            elif self.instance.author.id != session_user.id:
                raise ValidationException("You can only update card assigned to yourself", status.HTTP_400_BAD_REQUEST)

        if "status" in data and data["status"] == "PUBLISHED":
            if self.instance.test_status not in ["OK", "WARNING"]:
                raise ValidationException(
                    "This asset has to pass tests successfully before publishing", status.HTTP_400_BAD_REQUEST
                )

        if (
            "visibility" in data
            and data["visibility"] in ["PUBLIC", "UNLISTED"]
            and self.instance.test_status not in ["OK", "WARNING"]
        ):
            raise ValidationException("This asset has to pass tests successfully before publishing", code=400)

        if "slug" in data:
            data["slug"] = slugify(data["slug"]).lower()

        lang = self.instance.lang
        if "lang" in data:
            lang = data["lang"]

        category = self.instance.category
        if "category" in data:
            category = data["category"]

        if "superseded_by" in data and data["superseded_by"]:
            if data["superseded_by"].id == self.instance.id:
                raise ValidationException("One asset cannot supersed itself", code=400)

            try:
                _prev = data["superseded_by"].previous_version
                if _prev and (not self.instance.superseded_by or _prev.id != self.instance.superseded_by.id):
                    raise ValidationException(
                        f'Asset {data["superseded_by"].id} is already superseding {_prev.asset_type}: {_prev.slug}',
                        code=400,
                    )
            except Exception:
                pass

            try:
                previous_version = self.instance.previous_version
                if previous_version and data["superseded_by"].id == previous_version.id:
                    raise ValidationException("One asset cannot have its previous version also superseding", code=400)
            except Exception:
                pass

        if category is None:
            raise ValidationException("Asset category cannot be null", status.HTTP_400_BAD_REQUEST)

        if lang != category.lang:
            translated_category = category.all_translations.filter(lang=lang).first()
            if translated_category is None:
                raise ValidationException(
                    "Asset category is in a different language than the asset itself and we could not find a category translation that matches the same language",
                    status.HTTP_400_BAD_REQUEST,
                )
            data["category"] = translated_category

        validated_data = super().validate(data)
        return validated_data

    def update(self, instance, validated_data):

        data = {}

        if "status" in validated_data:
            if validated_data["status"] == "PUBLISHED" and instance.status != "PUBLISHED":
                now = timezone.now()
                data["published_at"] = now
            elif validated_data["status"] != "PUBLISHED":
                data["published_at"] = None

        # Check if preview img is being deleted
        if "preview" in validated_data:
            if validated_data["preview"] == None and instance.preview != None:
                hash = instance.preview.split("/")[-1]
                if hash is not None:
                    from .tasks import async_remove_asset_preview_from_cloud

                    async_remove_asset_preview_from_cloud.delay(hash)

        return super().update(instance, {**validated_data, **data})

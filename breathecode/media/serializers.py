from breathecode.admissions.models import Academy
from .models import Media, Category, MediaResolution
from slugify import slugify
from rest_framework import serializers
from breathecode.utils import serpy


class GetAcademySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class GetUserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()


class GetCategorySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    medias = serpy.MethodField()

    def get_medias(self, obj):
        return Media.objects.filter(categories__id=obj.id).count()


class GetMediaSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    mime = serpy.Field()
    url = serpy.Field()
    thumbnail = serpy.MethodField()
    hash = serpy.Field()
    hits = serpy.Field()
    categories = serpy.MethodField()
    academy = GetAcademySerializer(required=False)

    def get_thumbnail(self, obj):
        return obj.url + "-thumbnail"

    def get_categories(self, obj):
        return [GetCategorySerializer(x).data for x in obj.categories.all()]


class GetResolutionSerializer(serializers.ModelSerializer):
    id = serpy.Field()
    hash = serpy.Field()
    width = serpy.Field()
    height = serpy.Field()
    hits = serpy.Field()

    class Meta:
        model = MediaResolution
        fields = ("id", "hash", "width", "height", "hits")


class MediaListSerializer(serializers.ListSerializer):

    def update(self, instance, validated_data):
        ret = []

        for data in validated_data:
            item = [x for x in instance if x.id == data["id"]]
            item = item[0] if len(item) else None

            if "id" in data and not data["id"]:
                del data["id"]

            if "id" in data:
                if item and "categories" in data and data["categories"]:
                    item.categories.set(data["categories"])
                    del data["categories"]
                ret.append(self.child.update(item, data))

            else:
                ret.append(self.child.create(data))

        return ret


class MediaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    url = serializers.CharField(read_only=True, required=False)
    name = serializers.CharField(required=False)
    mime = serializers.CharField(read_only=True, required=False)
    hits = serializers.IntegerField(read_only=True, required=False)
    hash = serializers.CharField(read_only=True, required=False)
    slug = serializers.SlugField(required=False)

    class Meta:
        model = Media
        fields = ("id", "url", "thumbnail", "hash", "hits", "slug", "mime", "name", "categories", "academy")
        exclude = ()
        list_serializer_class = MediaListSerializer


class MediaPUTSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    url = serializers.CharField(required=False)
    thumbnail = serializers.CharField(required=False)
    hash = serializers.CharField()
    slug = serializers.SlugField()
    mime = serializers.CharField()
    name = serializers.CharField()

    class Meta:
        model = Media
        fields = ("id", "url", "thumbnail", "hash", "hits", "slug", "mime", "name", "categories", "academy")
        exclude = ()
        list_serializer_class = MediaListSerializer

    def validate(self, data):
        if "hash" in data and "academy" in data and isinstance(data["academy"], Academy):
            data["id"] = (
                Media.objects.filter(hash=data["hash"], academy__id=data["academy"].id)
                .values_list("id", flat=True)
                .first()
            )

        return data


class CategorySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    slug = serializers.SlugField(required=False)
    name = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Category
        fields = ("name", "slug", "created_at", "id")

    def create(self, validated_data):

        _slug = slugify(validated_data["name"])
        result = super().create({**validated_data, "slug": _slug})
        return result

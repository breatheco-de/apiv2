from .models import Media, Category
from rest_framework import serializers
import serpy


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
    hash = serpy.Field()
    hits = serpy.Field()
    categories = serpy.MethodField()
    owner = GetUserSerializer(required=False)

    def get_categories(self, obj):
        return [GetCategorySerializer(x).data for x in obj.categories.all()]


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        exclude = ()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        exclude = ()

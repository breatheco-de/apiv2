from breathecode.admissions.models import Academy
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
    url = serializers.CharField(read_only=True, required=False)
    name = serializers.CharField(read_only=True, required=False)
    mime = serializers.CharField(read_only=True, required=False)
    hits = serializers.IntegerField(read_only=True, required=False)
    hash = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Media
        exclude = ()


class MediaListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        books = [Media(**item) for item in validated_data]
        items = Media.objects.bulk_create(books)

        print(validated_data, 'lllllllllllllllllllllllllllllllllllll')
        for key in range(0, len(items)):
            item = items[key]
            items[key].id = Media.objects.filter(cohort__id=item.cohort_id, user__id=item.user_id).values_list('id', flat=True).first()

        return items

    def update(self, instance, validated_data):
        # Maps for id->instance and id->data item.
        print('===== update serializer')
        print(instance)
        print(validated_data)
        print('===== update serializer')
        model_mapping = {model.id: model for model in instance}
        data_mapping = {
            Media.objects.filter(academy__id=item['academy'].id,
                hash=item['hash']): item for item in validated_data
        }

        # Perform creations and updates.
        ret = []
        for model_id, data in data_mapping.items():
            book = model_mapping.get(model_id, None)
            if book is None:
                ret.append(self.child.create(data))
            else:
                ret.append(self.child.update(book, data))

        # Perform deletions.
        for model_id, model in model_mapping.items():
            if model_id not in data_mapping:
                model.delete()

        return ret


class MediaPUTSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    url = serializers.CharField(required=False)
    hash = serializers.CharField()
    slug = serializers.SlugField()
    mime = serializers.CharField()
    name = serializers.CharField()
    # categories = serializers.PrimaryKeyRelatedField(many=True, required=False, queryset=Category.objects.all())
    # academy = serializers.PrimaryKeyRelatedField(queryset=Academy.objects.all(), required=False)

    class Meta:
        model = Media
        # fields = ('id', 'hash', 'slug', 'mime', 'name', 'categories', 'academy')
        exclude = ()
        list_serializer_class = MediaListSerializer

    def validate(self, data):
        # print('uuuuuuuuuuuu', data)
        return data
        # return self.context


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        exclude = ()

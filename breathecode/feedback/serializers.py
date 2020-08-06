from .models import Answer
from rest_framework import serializers
import serpy

class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()

class AnswerSerializer(serpy.Serializer):
    id = serpy.Field()
    comment = serpy.Field()
    score = serpy.Field()
    user = UserSerializer(required=False)

    enity_type = serpy.Field(required=False)
    entity_id = serpy.Field(required=False)
    entity_slug = serpy.Field(required=False)

class AnswerPOSTSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        exclude = ()

        
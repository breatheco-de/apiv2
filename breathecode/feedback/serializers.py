from .models import Answer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import serpy
from django.utils import timezone

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

    def validate(self, data):
        utc_now = timezone.now()
        # the user cannot vote to the same entity within 5 minutes
        recent_answer = Answer.objects.filter(
            user=self.context['request'].user, 
            entity_id=data['entity_id'], 
            created_at__gte= utc_now - timezone.timedelta(minutes=5)
        ).first()
        if recent_answer:
            raise ValidationError('You have already voted')

        if int(data['score']) > 10 or int(data['score']) < 1:
            raise ValidationError('Answer score must be between 1 and 10')

        return data

    def create(self, validated_data):
        entity = Answer.objects.create(**{ **validated_data, "user": self.context['request'].user})
        return entity

        
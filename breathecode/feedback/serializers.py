from breathecode.authenticate.models import Token
from .models import Answer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import serpy
from django.utils import timezone

class GetAcademySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()

class GetCohortSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()

class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()

class EventTypeSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    description = serpy.Field()
    excerpt = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()

class AnswerSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    lowest = serpy.Field()
    highest = serpy.Field()
    lang = serpy.Field()
    comment = serpy.Field()
    score = serpy.Field()
    status = serpy.Field()
    created_at = serpy.Field()
    user = UserSerializer(required=False)

    score = serpy.Field()
    academy = GetAcademySerializer(required=False)
    cohort = GetCohortSerializer(required=False)
    mentor = UserSerializer(required=False)
    event = EventTypeSmallSerializer(required=False)

class AnswerPUTSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        exclude = ('token',)

    def validate(self, data):
        utc_now = timezone.now()

        # the user cannot vote to the same entity within 5 minutes
        answer = Answer.objects.filter(user=self.context['request'].user,id=self.context['answer']).first()
        if answer is None:
            raise ValidationError('This survey does not exist for this user')

        if not 'score' in data or int(data['score']) > 10 or int(data['score']) < 1:
            raise ValidationError('Score must be between 1 and 10')
        
        if answer.status == 'ANSWERED' and data['score'] != answer.score:
            raise ValidationError(f'You have already answered {answer.score}, you must keep the same score')


        return data

    def update(self, instance, validated_data):
        instance.score = validated_data['score']
        instance.status = 'ANSWERED'
        # instance.token = None

        if 'comment' in validated_data:
            instance.comment = validated_data['comment']

        instance.save()

        return instance

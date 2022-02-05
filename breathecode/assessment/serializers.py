from .models import Answer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import serpy
from django.utils import timezone


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class GetOptionSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    help_text = serpy.Field()
    score = serpy.Field()


class GetQuestionSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    help_text = serpy.Field()
    question_type = serpy.Field()

    options = serpy.MethodField()

    def get_options(self, obj):
        return GetOptionSerializer(obj.option_set.all(), many=True).data


class GetAssessmentSerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    score_threshold = serpy.Field()
    private = serpy.Field()
    translations = serpy.MethodField()

    def get_translations(self, obj):
        if obj.translations is None:
            return []
        return [t.lang for t in obj.translations.all()]


class GetAssessmentBigSerializer(GetAssessmentSerializer):
    questions = serpy.MethodField()

    def get_questions(self, obj):
        return GetQuestionSerializer(obj.question_set.all(), many=True).data

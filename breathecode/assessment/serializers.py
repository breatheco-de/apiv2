from .models import Answer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import serpy
from django.utils import timezone

class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()

class GetQuestionSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    help_text = serpy.Field()
    question_type = serpy.Field()

class GetAssessmentSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    score_threshold = serpy.Field()
    private = serpy.Field()

class GetAssessmentBigSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    score_threshold = serpy.Field()
    private = serpy.Field()
    questions = serpy.MethodField()

    def get_questions(self, obj):
        return GetQuestionSerializer(obj.question_set, many=True).data
        
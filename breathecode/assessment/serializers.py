from breathecode.utils import serpy
from .models import Assessment, Question, Option
from rest_framework import serializers


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class AssessmentSmallSerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()


class GetAssessmentThresholdSerializer(serpy.Serializer):
    success_next = serpy.Field()
    fail_next = serpy.Field()
    success_message = serpy.Field()
    fail_message = serpy.Field()
    score_threshold = serpy.Field()
    assessment = AssessmentSmallSerializer()


class GetOptionSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    help_text = serpy.Field()
    score = serpy.Field()
    position = serpy.Field()


class GetQuestionSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    position = serpy.Field()
    help_text = serpy.Field()
    question_type = serpy.Field()

    options = serpy.MethodField()

    def get_options(self, obj):
        return GetOptionSerializer(obj.option_set.filter(is_deleted=False), many=True).data


class GetAssessmentSerializer(serpy.Serializer):
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    private = serpy.Field()
    translations = serpy.MethodField()

    def get_translations(self, obj):
        if obj.translations is None:
            return []
        return [t.lang for t in obj.translations.all()]


class GetAssessmentBigSerializer(GetAssessmentSerializer):
    questions = serpy.MethodField()
    is_instant_feedback = serpy.Field()

    def get_questions(self, obj):
        return GetQuestionSerializer(obj.question_set.filter(is_deleted=False).order_by('-position', 'id'),
                                     many=True).data


class OptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Option
        exclude = ('created_at', 'updated_at')


class QuestionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Question
        exclude = ('created_at', 'updated_at', 'assessment')


class AssessmentPUTSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assessment
        exclude = ('slug', 'academy', 'lang', 'author')

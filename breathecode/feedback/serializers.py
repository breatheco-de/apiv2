from breathecode.authenticate.models import Token
from breathecode.admissions.models import CohortUser, Cohort
from breathecode.admissions.serializers import CohortSerializer
from breathecode.utils import ValidationException
from .models import Answer, Survey
from .actions import send_survey_group
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import serpy, re
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

class BigAnswerSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    lowest = serpy.Field()
    highest = serpy.Field()
    lang = serpy.Field()
    comment = serpy.Field()
    score = serpy.Field()
    status = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()
    opened_at = serpy.Field()
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


class SurveySerializer(serializers.ModelSerializer):
    send_now = serializers.BooleanField(required=False, write_only=True)
    public_url = serializers.SerializerMethodField()

    def get_public_url(self, obj):
        return "https://nps.breatheco.de/survey/" + str(obj.id)

    class Meta:
        model = Survey
        exclude = ('avg_score', 'status_json', 'status')

    def validate(self, data):

        if not 'cohort' in data:
            raise ValidationException('No cohort has been specified for this survey')

        if data["cohort"].academy.id != int(self.context['academy_id']):
            raise ValidationException(f'You don\'t have rights for this cohort academy {self.context["academy_id"]}')

        reg = re.compile('^[0-9]{0,3}\s[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}$')
        if "duration" in data and data["duration"] < timezone.timedelta(hours=1):
            raise ValidationException(f'Minimum duration for surveys is one hour')

        cohort_teacher = CohortUser.objects.filter(cohort=data["cohort"], role="TEACHER")
        if cohort_teacher.count() == 0:
            raise ValidationException("This cohort must have a teacher assigned to be able to survey it", 400)
        
        return data

    def create(self, validated_data):

        send_now = False
        if "send_now" in validated_data:
            if validated_data["send_now"]:
                send_now = True
            del validated_data["send_now"]

        cohort = validated_data["cohort"]

        if "lang" not in validated_data:
            validated_data["lang"] = cohort.language

        
        result = super().create(validated_data)

        if send_now:
            send_survey_group(survey=result)

        return result

class SurveyPUTSerializer(serializers.ModelSerializer):
    send_now = serializers.BooleanField(required=False, write_only=True)
    cohort = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = Survey
        exclude = ('avg_score', 'status_json', 'status')

    def validate(self, data):

        if self.instance.status != 'PENDING':
            raise ValidationException("This survey was already send, therefore it cannot be updated")

        if 'cohort' in data:
            raise ValidationException("The cohort cannot be updated in a survey, please create a new survey instead.")

        if self.instance.cohort.academy.id != int(self.context['academy_id']):
            raise ValidationException('You don\'t have rights for this cohort academy')
        
        return data

    def update(self, instance, validated_data):

        send_now = False
        if "send_now" in validated_data:
            if validated_data["send_now"]:
                send_now = True
            del validated_data["send_now"]

        result = super().update(instance, validated_data)

        if send_now:
            send_survey_group(survey=result)

        return result

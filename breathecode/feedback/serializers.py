from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

import breathecode.feedback.actions as actions
from breathecode.admissions.models import CohortUser
from breathecode.utils import serpy
from capyc.rest_framework.exceptions import ValidationException

from .actions import send_survey_group
from .models import Answer, Review, Survey


class GetAcademySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class GetCohortSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class GetProfileSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    profile = serpy.MethodField()

    def get_profile(self, obj):
        if not hasattr(obj, "profile"):
            return None

        return GetProfileSmallSerializer(obj.profile).data


class GithubSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()
    name = serpy.Field()
    username = serpy.Field()


class UserSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    email = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    github = serpy.MethodField()

    def get_github(self, obj):
        if not hasattr(obj, "credentialsgithub"):
            return None

        return GithubSmallSerializer(obj.credentialsgithub).data


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

    academy = GetAcademySerializer(required=False)
    cohort = GetCohortSerializer(required=False)
    mentor = UserSerializer(required=False)
    event = EventTypeSmallSerializer(required=False)


class SurveySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    lang = serpy.Field()
    cohort = GetCohortSerializer()
    scores = serpy.Field()
    response_rate = serpy.Field()
    status = serpy.Field()
    status_json = serpy.Field()
    duration = serpy.Field()
    created_at = serpy.Field()
    sent_at = serpy.Field()
    public_url = serpy.MethodField()

    def get_public_url(self, obj):
        return "https://nps.4geeks.com/survey/" + str(obj.id)


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


class ReviewPlatformSerializer(serpy.Serializer):
    slug = serpy.Field()
    name = serpy.Field()
    website = serpy.Field()


class ReviewSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    total_rating = serpy.Field()
    nps_previous_rating = serpy.Field()
    public_url = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    cohort = GetCohortSerializer()
    author = UserSerializer()
    comments = serpy.Field()
    lang = serpy.Field()
    platform = ReviewPlatformSerializer()
    updated_at = serpy.Field()


class AnswerPUTSerializer(serializers.ModelSerializer):

    class Meta:
        model = Answer
        exclude = ("token",)

    def validate(self, data):

        # the user cannot vote to the same entity within 5 minutes
        answer = Answer.objects.filter(user=self.context["request"].user, id=self.context["answer"]).first()
        if answer is None:
            raise ValidationError("This survey does not exist for this user")

        if not "score" in data or int(data["score"]) > 10 or int(data["score"]) < 1:
            raise ValidationError("Score must be between 1 and 10")

        if answer.status == "ANSWERED" and data["score"] != answer.score:
            raise ValidationError(f"You have already answered {answer.score}, you must keep the same score")

        return data

    def update(self, instance, validated_data):
        instance.score = validated_data["score"]
        instance.status = "ANSWERED"
        # instance.token = None

        if "comment" in validated_data:
            instance.comment = validated_data["comment"]

        instance.save()

        return instance


class SurveySerializer(serializers.ModelSerializer):
    send_now = serializers.BooleanField(required=False, write_only=True)
    status = serializers.BooleanField(required=False, read_only=True)
    public_url = serializers.SerializerMethodField()

    def get_public_url(self, obj):
        return "https://nps.4geeks.com/survey/" + str(obj.id)

    class Meta:
        model = Survey
        exclude = ("scores", "status_json", "response_rate")

    def validate(self, data):

        if data["cohort"].academy.id != int(self.context["academy_id"]):
            raise ValidationException(
                f'You don\'t have rights for this cohort academy {self.context["academy_id"]}.',
                code=400,
                slug="cohort-academy-needs-rights",
            )

        if "duration" in data and data["duration"] < timezone.timedelta(hours=1):
            raise ValidationException(
                "Minimum duration for surveys is one hour.", code=400, slug="minimum-survey-duration-1h"
            )

        cohort_teacher = CohortUser.objects.filter(cohort=data["cohort"], role="TEACHER")
        if cohort_teacher.count() == 0:
            raise ValidationException(
                "This cohort must have a teacher assigned to be able to survey it",
                code=400,
                slug="cohort-needs-teacher-assigned",
            )

        return data

    def create(self, validated_data):

        send_now = False
        if "send_now" in validated_data:
            if validated_data["send_now"]:
                send_now = True
            del validated_data["send_now"]

        cohort = validated_data["cohort"]

        if "lang" not in validated_data:
            validated_data["lang"] = cohort.language.lower()

        result = super().create(validated_data)

        if send_now:
            actions.send_survey_group(survey=result)

        return result


class SurveyPUTSerializer(serializers.ModelSerializer):
    send_now = serializers.BooleanField(required=False, write_only=True)
    cohort = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = Survey
        exclude = ("scores", "status_json", "status", "response_rate")

    def validate(self, data):

        if self.instance.status != "PENDING":
            raise ValidationException("This survey was already send, therefore it cannot be updated")

        if "cohort" in data:
            raise ValidationException("The cohort cannot be updated in a survey, please create a new survey instead.")

        if self.instance.cohort.academy.id != int(self.context["academy_id"]):
            raise ValidationException("You don't have rights for this cohort academy")

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


class ReviewPUTSerializer(serializers.ModelSerializer):

    class Meta:
        model = Review
        exclude = ("created_at", "updated_at", "author", "platform", "nps_previous_rating")

    def validate(self, data):

        if "cohort" in data:
            raise ValidationException("The cohort cannot be updated in a review, please create a new review instead.")

        if "author" in data:
            raise ValidationException("The author cannot be updated in a review, please create a new review instead.")

        if "platform" in data:
            raise ValidationException("The platform cannot be updated in a review, please create a new review instead.")

        if self.instance.cohort.academy.id != int(self.context["academy_id"]):
            raise ValidationException("You don't have rights for this cohort academy")

        return data

    def update(self, instance, validated_data):
        result = super().update(instance, validated_data)
        return result

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework import serializers

from breathecode.admissions.models import Academy
from breathecode.utils import serpy
from breathecode.utils.datetime_integer import duration_to_str, from_now
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

from .models import Answer, Assessment, Option, Question, UserAssessment


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class AcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class AssessmentSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()


class QuestionSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    question_type = serpy.Field()
    is_deleted = serpy.Field()
    position = serpy.Field()


class OptionSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    score = serpy.Field()


class AnswerSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    option = OptionSmallSerializer()
    question = QuestionSmallSerializer()
    value = serpy.Field()


class GetAssessmentLayoutSerializer(serpy.Serializer):
    slug = serpy.Field()
    additional_styles = serpy.Field()
    variables = serpy.Field()
    created_at = serpy.Field()
    academy = AcademySmallSerializer()


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
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    private = serpy.Field()
    translations = serpy.MethodField()

    def get_translations(self, obj):
        if obj.translations is None:
            return []
        return [t.lang for t in obj.translations.all()]


class SmallUserAssessmentSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()

    assessment = AssessmentSmallSerializer()

    owner = UserSerializer(required=False)
    owner_email = serpy.Field()

    total_score = serpy.Field()

    started_at = serpy.Field()
    finished_at = serpy.Field()

    created_at = serpy.Field()


class GetUserAssessmentSerializer(serpy.Serializer):
    id = serpy.Field()
    token = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()

    academy = AcademySmallSerializer(required=False)
    assessment = AssessmentSmallSerializer()

    owner = UserSerializer(required=False)
    owner_email = serpy.Field()
    owner_phone = serpy.Field()

    status = serpy.Field()
    status_text = serpy.Field()

    conversion_info = serpy.Field()
    total_score = serpy.Field()
    comment = serpy.Field()

    started_at = serpy.Field()
    finished_at = serpy.Field()

    created_at = serpy.Field()


class PublicUserAssessmentSerializer(serpy.Serializer):
    id = serpy.Field()
    token = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()

    academy = AcademySmallSerializer(required=False)
    assessment = AssessmentSmallSerializer()

    owner = UserSerializer(required=False)
    owner_email = serpy.Field()
    owner_phone = serpy.Field()

    status = serpy.Field()
    status_text = serpy.Field()

    conversion_info = serpy.Field()
    comment = serpy.Field()

    started_at = serpy.Field()
    finished_at = serpy.Field()

    created_at = serpy.Field()

    summary = serpy.MethodField()

    def get_summary(self, obj):
        total_score, last_one = obj.get_score()

        last_answer = None
        if last_one is not None:
            last_answer = AnswerSmallSerializer(last_one).data

        return {"last_answer": last_answer, "live_score": total_score}


class GetAssessmentBigSerializer(GetAssessmentSerializer):
    questions = serpy.MethodField()
    is_instant_feedback = serpy.Field()

    def get_questions(self, obj):
        return GetQuestionSerializer(
            obj.question_set.filter(is_deleted=False).order_by("-position", "id"), many=True
        ).data


class OptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Option
        exclude = ("created_at", "updated_at")


class QuestionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Question
        exclude = ("created_at", "updated_at", "assessment")


class AnswerSerializer(serializers.ModelSerializer):
    token = serializers.CharField()

    class Meta:
        model = Answer
        exclude = ("created_at", "updated_at")

    def validate(self, data):

        lang = self.context["lang"]
        validated_data = {**data}
        del validated_data["token"]

        uass = UserAssessment.objects.filter(token=data["token"]).first()
        if not uass:
            raise ValidationException(
                translation(
                    lang,
                    en="user assessment not found for this token",
                    es="No se han encontrado un user assessment con ese token",
                    slug="not-found",
                )
            )
        validated_data["user_assessment"] = uass

        now = timezone.now()
        session_duration = uass.created_at
        max_duration = uass.created_at + uass.assessment.max_session_duration
        if now > max_duration:
            raise ValidationException(
                f"User assessment session started {from_now(session_duration)} ago and it expires after {duration_to_str(uass.assessment.max_session_duration)}, no more updates can be made"
            )

        if "option" in data and data["option"]:
            if Answer.objects.filter(option=data["option"], user_assessment=uass).count() > 0:
                raise ValidationException(
                    translation(
                        lang,
                        en="This answer has already been answered on this user assessment",
                        es="Esta opción ya fue respondida para este assessment",
                        slug="already-answered",
                    )
                )

        return super().validate(validated_data)

    def create(self, validated_data):

        # copy the validated data just to do small last minute corrections
        data = validated_data.copy()

        if "option" in data and data["option"]:
            data["question"] = data["option"].question

            if data["question"].question_type == "SELECT":
                data["value"] = data["option"].score

        return super().create({**data})


class AssessmentPUTSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assessment
        exclude = ("slug", "academy", "lang", "author")


class PostUserAssessmentSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(required=False)

    class Meta:
        model = UserAssessment
        exclude = ("total_score", "created_at", "updated_at", "token", "owner")
        read_only_fields = ["id"]

    def validate(self, data):

        lang = self.context["lang"]
        request = self.context["request"]

        if "status" in data and data["status"] not in ["DRAFT", "SENT"]:
            raise ValidationException(
                translation(
                    lang,
                    en=f'User assessment cannot be created with status {data["status"]}',
                    es=f'El user assessment no se puede crear con status {data["status"]}',
                    slug="invalid-status",
                )
            )

        academy = None
        if "Academy" in request.headers:
            academy_id = request.headers["Academy"]
            academy = Academy.objects.filter(id=academy_id).first()

        if not academy and "academy" in data:
            academy = data["academy"]

        if not academy and "assessment" in data:
            academy = data["assessment"].academy

        if not academy:
            raise ValidationException(
                translation(
                    lang,
                    en="Could not determine academy ownership of this user assessment",
                    es="No se ha podido determinar a que academia pertenece este user assessment",
                    slug="not-academy-detected",
                )
            )

        if not isinstance(request.user, AnonymousUser):
            data["owner"] = request.user
        elif "owner_email" not in data or not data["owner_email"]:
            raise ValidationException(
                translation(
                    lang,
                    en="User assessment cannot be tracked because its missing owner information",
                    es="Este user assessment no puede registrarse porque no tiene informacion del owner",
                    slug="no-owner-detected",
                )
            )

        return super().validate({**data, "academy": academy})

    def create(self, validated_data):

        # copy the validated data just to do small last minute corrections
        data = validated_data.copy()

        if data["academy"] is None:
            data["status"] = "ERROR"
            data["status_text"] = "Missing academy. Maybe the assessment.academy is null?"

        # "us" language will become "en" language, its the right lang code
        if "lang" in data and data["lang"] == "us":
            data["lang"] = "en"

        if "started_at" not in data or data["started_at"] is None:
            data["started_at"] = timezone.now()

        if "title" not in data or not data["title"]:
            if "owner_email" in data and data["owner_email"]:
                data["title"] = f"{data['assessment'].title} from {data['owner_email']}"
            if "owner" in data and data["owner"]:
                data["title"] = f"{data['assessment'].title} from {data['owner'].email}"

        result = super().create({**data, "total_score": 0, "academy": validated_data["academy"]})
        return result


class PUTUserAssessmentSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False)

    class Meta:
        model = UserAssessment
        exclude = ("academy", "assessment", "lang", "total_score", "token", "started_at", "owner")
        read_only_fields = [
            "id",
            "academy",
        ]

    def validate(self, data):

        lang = self.context["lang"]

        if self.instance.status not in ["DRAFT", "SENT", "ERROR"]:
            raise ValidationException(
                translation(
                    lang,
                    en=f"User assessment cannot be updated because is {self.instance.status}",
                    es=f"El user assessment status no se puede editar mas porque esta {self.instance.status}",
                    slug="invalid-status",
                )
            )

        return super().validate({**data})

    def update(self, instance, validated_data):

        # NOTE: User Assignments that are closed will be automatically scored with assessment.task.async_close_userassignment
        now = timezone.now()
        data = validated_data.copy()

        # If not being closed
        if validated_data["status"] != "ANSWERED" or instance.status == validated_data["status"]:
            if now > (instance.created_at + instance.assessment.max_session_duration):
                raise ValidationException(
                    f"Session started {from_now(instance.created_at)} ago and it expires after {duration_to_str(instance.assessment.max_session_duration)}, no more updates can be made"
                )

        # copy the validated data just to do small last minute corrections
        data = validated_data.copy()
        if "status_text" in data:
            del data["status_text"]

        # "us" language will become "en" language, its the right lang code
        if "lang" in data and data["lang"] == "us":
            data["lang"] = "en"

        if "started_at" not in data and instance.started_at is None:
            data["started_at"] = now

        return super().update(instance, data)

from capyc.rest_framework.exceptions import ValidationException
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

import breathecode.feedback.actions as actions
from breathecode.admissions.models import CohortUser
from breathecode.utils import serpy

from .actions import send_cohort_survey_group
from .models import (
    AcademyFeedbackSettings,
    Answer,
    FeedbackTag,
    Review,
    Survey,
    SurveyConfiguration,
    SurveyQuestionTemplate,
    SurveyResponse,
    SurveyStudy,
)


class GetAcademySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class MentorshipSessionSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()
    starts_at = serpy.Field()
    ends_at = serpy.Field()


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


class SurveyTemplateSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    lang = serpy.Field()
    is_shared = serpy.Field()
    when_asking_event = serpy.Field()
    when_asking_mentor = serpy.Field()
    when_asking_cohort = serpy.Field()
    when_asking_academy = serpy.Field()
    when_asking_mentorshipsession = serpy.Field()
    when_asking_platform = serpy.Field()
    when_asking_liveclass_mentor = serpy.Field()
    when_asking_mentor_communication = serpy.Field()
    when_asking_mentor_participation = serpy.Field()
    additional_questions = serpy.Field()
    original = serpy.MethodField()

    def get_original(self, obj):
        if obj.original is None:
            return None
        return {
            "id": obj.original.id,
            "slug": obj.original.slug,
        }


class LiveClassSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    started_at = serpy.Field()
    ended_at = serpy.Field()


class AssetSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()


class AnswerSerializer(serpy.Serializer):
    id = serpy.Field()
    question_by_slug = serpy.Field()
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
    live_class = LiveClassSmallSerializer(required=False)
    asset = AssetSmallSerializer(required=False)
    mentorship_session = MentorshipSessionSmallSerializer(required=False)


class SurveySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    lang = serpy.Field()
    title = serpy.Field(required=False)
    template_slug = serpy.Field(required=False)
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


class GetSurveySerializer(serpy.Serializer):
    id = serpy.Field()
    send_now = serpy.Field(required=False)
    status = serpy.Field(required=False)
    public_url = serpy.MethodField()
    lang = serpy.Field(required=False)
    max_assistants_to_ask = serpy.Field(required=False)
    max_teachers_to_ask = serpy.Field(required=False)
    duration = serpy.Field(required=False)
    created_at = serpy.Field()
    updated_at = serpy.Field()
    sent_at = serpy.Field(required=False)
    cohort = serpy.MethodField()
    scores = serpy.Field()

    def get_public_url(self, obj):
        return "https://nps.4geeks.com/survey/" + str(obj.id)

    def get_cohort(self, obj):
        return obj.cohort.id if obj.cohort else None


class AcademyFeedbackSettingsSerializer(serpy.Serializer):
    """Serializer for AcademyFeedbackSettings"""

    id = serpy.Field()
    cohort_survey_template = SurveyTemplateSerializer(required=False)
    liveclass_survey_template = SurveyTemplateSerializer(required=False)
    event_survey_template = SurveyTemplateSerializer(required=False)
    mentorship_session_survey_template = SurveyTemplateSerializer(required=False)
    liveclass_survey_cohort_exclusions = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class FeedbackTagSerializer(serpy.Serializer):
    """Serializer for FeedbackTag (read operations)"""

    id = serpy.Field()
    slug = serpy.Field()
    title = serpy.Field()
    description = serpy.Field()
    priority = serpy.Field()
    is_private = serpy.Field()
    academy = GetAcademySerializer(required=False)
    created_at = serpy.Field()
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
            actions.send_cohort_survey_group(survey=result)

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
            send_cohort_survey_group(survey=result)

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


class AcademyFeedbackSettingsPUTSerializer(serializers.ModelSerializer):
    """Serializer for updating AcademyFeedbackSettings"""

    class Meta:
        model = AcademyFeedbackSettings
        exclude = ("academy", "created_at", "updated_at")


class FeedbackTagPOSTSerializer(serializers.ModelSerializer):
    """Serializer for creating FeedbackTag"""

    class Meta:
        model = FeedbackTag
        exclude = ("created_at", "updated_at")

    def validate(self, data):
        # Validate that if is_private is True, academy must be set
        if data.get("is_private", False) and not data.get("academy"):
            raise ValidationException(
                "Private tags must have an academy assigned", code=400, slug="private-tag-needs-academy"
            )

        # Validate that public shared tags (academy=None, is_private=False) are valid
        if not data.get("academy") and not data.get("is_private", False):
            # This is a public shared tag - allowed
            pass

        return data


class FeedbackTagPUTSerializer(serializers.ModelSerializer):
    """Serializer for updating FeedbackTag"""

    class Meta:
        model = FeedbackTag
        exclude = ("created_at", "updated_at", "slug")

    def validate(self, data):
        # Cannot change slug
        if "slug" in data and data["slug"] != self.instance.slug:
            raise ValidationException("Cannot change tag slug", code=400, slug="cannot-change-slug")

        # Validate that if is_private is True, academy must be set
        is_private = data.get("is_private", self.instance.is_private)
        academy = data.get("academy", self.instance.academy)

        if is_private and not academy:
            raise ValidationException(
                "Private tags must have an academy assigned", code=400, slug="private-tag-needs-academy"
            )

        return data


class SurveyResponseHookSerializer(serpy.Serializer):
    """Serializer for webhook payload when a survey response is answered."""

    id = serpy.Field()
    survey_response_id = serpy.MethodField()
    user_id = serpy.MethodField()
    user_email = serpy.MethodField()
    trigger_type = serpy.MethodField()
    trigger_context = serpy.Field()
    answers = serpy.Field()
    answers_detail = serpy.MethodField()
    status = serpy.Field()
    answered_at = serpy.Field()
    created_at = serpy.Field()

    def get_survey_response_id(self, obj):
        return obj.id

    def get_user_id(self, obj):
        return obj.user.id if obj.user else None

    def get_user_email(self, obj):
        return obj.user.email if obj.user else None

    def get_trigger_type(self, obj):
        return obj.survey_config.trigger_type if obj.survey_config else None

    def get_answers_detail(self, obj):
        """
        Human-readable answers: each item contains the question definition (from the config) + the user's answer.

        This keeps `answers` as the canonical machine-friendly mapping (question_id -> value),
        while providing an easier structure for humans/BI.
        """
        if not obj or not getattr(obj, "survey_config", None):
            return []

        questions = {}
        try:
            raw_questions = (obj.survey_config.questions or {}).get("questions", []) or []
            if isinstance(raw_questions, list):
                for q in raw_questions:
                    if isinstance(q, dict) and q.get("id"):
                        questions[q["id"]] = q
        except Exception:
            questions = {}

        answers = obj.answers or {}
        if not isinstance(answers, dict):
            return []

        ordered_ids = []
        try:
            raw_questions = (obj.survey_config.questions or {}).get("questions", []) or []
            for q in raw_questions:
                qid = q.get("id") if isinstance(q, dict) else None
                if qid and qid in answers:
                    ordered_ids.append(qid)
        except Exception:
            ordered_ids = []

        # Include any extra answers not present in the questions list (defensive)
        for qid in answers.keys():
            if qid not in ordered_ids:
                ordered_ids.append(qid)

        result = []
        for qid in ordered_ids:
            result.append(
                {
                    "id": qid,
                    "question": questions.get(qid),
                    "answer": answers.get(qid),
                }
            )

        return result


class SurveyConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for creating and listing survey configurations."""

    class Meta:
        model = SurveyConfiguration
        fields = [
            "id",
            "trigger_type",
            "syllabus",
            "template",
            "questions",
            "is_active",
            "academy",
            "cohorts",
            "asset_slugs",
            "priority",
            "created_by",
            "created_at",
            "updated_at",
        ]
        # academy and created_by are set by the view based on the Academy header and the authenticated user
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "academy"]

        extra_kwargs = {
            "academy": {"required": False},
            "trigger_type": {"required": False, "allow_null": True},
            "questions": {"required": False},
            "syllabus": {"required": False},
            "priority": {"required": False, "allow_null": True},
        }

    def validate_syllabus(self, value):
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise ValidationException("syllabus must be a dictionary", slug="invalid-syllabus-filter")

        allowed_keys = {"syllabus", "version", "module", "asset_slug"}
        for k in value.keys():
            if k not in allowed_keys:
                raise ValidationException(f"Invalid syllabus key: {k}", slug="invalid-syllabus-filter-key")

        if "syllabus" in value and value["syllabus"] is not None and not isinstance(value["syllabus"], str):
            raise ValidationException("'syllabus' must be a string", slug="invalid-syllabus-filter-syllabus")

        if "version" in value and value["version"] is not None:
            if not isinstance(value["version"], int) or value["version"] < 1:
                raise ValidationException("'version' must be an integer >= 1", slug="invalid-syllabus-filter-version")

        if "module" in value and value["module"] is not None:
            if not isinstance(value["module"], int) or value["module"] < 0:
                raise ValidationException("'module' must be an integer >= 0", slug="invalid-syllabus-filter-module")

        if "asset_slug" in value and value["asset_slug"] is not None and not isinstance(value["asset_slug"], str):
            raise ValidationException("'asset_slug' must be a string", slug="invalid-syllabus-filter-asset-slug")
        
        return value

    def validate_questions(self, value):
        """Validate questions structure."""
        if not isinstance(value, dict):
            raise ValidationException("questions must be a dictionary", slug="invalid-questions-structure")

        if "questions" not in value:
            raise ValidationException("questions must contain a 'questions' key", slug="missing-questions-key")

        questions = value.get("questions", [])
        if not isinstance(questions, list):
            raise ValidationException("questions.questions must be a list", slug="invalid-questions-list")

        if len(questions) == 0:
            raise ValidationException("questions.questions must contain at least one question", slug="empty-questions-list")

        for idx, question in enumerate(questions):
            if not isinstance(question, dict):
                raise ValidationException(
                    f"Question at index {idx} must be a dictionary", slug="invalid-question-structure"
                )

            required_fields = ["id", "type", "title"]
            for field in required_fields:
                if field not in question:
                    raise ValidationException(
                        f"Question at index {idx} missing required field: {field}", slug=f"missing-{field}"
                    )

            question_type = question.get("type")
            if question_type == "likert_scale":
                config = question.get("config", {})
                scale = config.get("scale", 5)
                if not isinstance(scale, int) or scale < 1:
                    raise ValidationException(
                        f"Question {question.get('id')} likert_scale must have scale >= 1",
                        slug="invalid-likert-scale",
                    )

            elif question_type == "open_question":
                config = question.get("config", {})
                max_length = config.get("max_length", 500)
                if not isinstance(max_length, int) or max_length < 1:
                    raise ValidationException(
                        f"Question {question.get('id')} open_question must have max_length >= 1",
                        slug="invalid-open-question-max-length",
                    )

        return value

    def validate(self, data):
        """
        Enforce mutual exclusivity:
        - If template is provided, questions may be omitted (it will be sourced from template on save()).
        - If template is not provided, questions must exist.
        """
        template = data.get("template", getattr(self.instance, "template", None) if self.instance else None)
        questions = data.get("questions", getattr(self.instance, "questions", None) if self.instance else None)

        # If template is set, questions must not be provided/edited via API to avoid divergence and confusion.
        if template is not None and "questions" in data:
            raise ValidationException(
                "questions cannot be modified when template is assigned",
                code=400,
                slug="questions-not-editable-with-template",
            )

        if template is None and not questions:
            raise ValidationException("questions is required when template is not provided", slug="missing-questions")

        return data


class SurveyResponseSerializer(serializers.ModelSerializer):
    """Serializer for survey responses."""

    answers_detail = serializers.SerializerMethodField()

    class Meta:
        model = SurveyResponse
        fields = [
            "id",
            "survey_config",
            "survey_study",
            "user",
            "token",
            "trigger_context",
            "questions_snapshot",
            "answers",
            "answers_detail",
            "status",
            "created_at",
            "opened_at",
            "email_opened_at",
            "answered_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "survey_config",
            "survey_study",
            "token",
            "trigger_context",
            "questions_snapshot",
            "status",
            "created_at",
            "opened_at",
            "email_opened_at",
            "answered_at",
        ]

    def get_answers_detail(self, obj):
        """
        Human-readable answers: ordered list of {id, question, answer}.

        - `question` is the original question dict from `survey_config.questions['questions']`
          (can include `en/es` translations if you store them that way).
        - `answer` is the raw value the user submitted (int for likert, str for open_question, etc).
        """
        if not obj or not getattr(obj, "survey_config", None):
            return []

        answers = obj.answers or {}
        if not isinstance(answers, dict):
            return []

        raw_questions = (obj.survey_config.questions or {}).get("questions", []) or []
        questions_by_id = {}
        if isinstance(raw_questions, list):
            for q in raw_questions:
                if isinstance(q, dict) and q.get("id"):
                    questions_by_id[q["id"]] = q

        ordered_ids = []
        if isinstance(raw_questions, list):
            for q in raw_questions:
                qid = q.get("id") if isinstance(q, dict) else None
                if qid and qid in answers:
                    ordered_ids.append(qid)

        for qid in answers.keys():
            if qid not in ordered_ids:
                ordered_ids.append(qid)

        return [{"id": qid, "question": questions_by_id.get(qid), "answer": answers.get(qid)} for qid in ordered_ids]


class SurveyQuestionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyQuestionTemplate
        fields = ["id", "slug", "title", "description", "questions", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_questions(self, value):
        # Reuse the same shape as SurveyConfiguration.questions
        if not isinstance(value, dict):
            raise ValidationException("questions must be a dictionary", slug="invalid-questions-structure")

        if "questions" not in value:
            raise ValidationException("questions must contain a 'questions' key", slug="missing-questions-key")

        questions = value.get("questions", [])
        if not isinstance(questions, list):
            raise ValidationException("questions.questions must be a list", slug="invalid-questions-list")

        if len(questions) == 0:
            raise ValidationException("questions.questions must contain at least one question", slug="empty-questions-list")

        return value


class SurveyStudySerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyStudy
        fields = [
            "id",
            "slug",
            "title",
            "description",
            "academy",
            "starts_at",
            "ends_at",
            "max_responses",
            "survey_configurations",
            "stats",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "academy", "stats", "created_at", "updated_at"]

    def validate_survey_configurations(self, value):
        """
        Validate that all survey configurations in a study have the same trigger_type.
        
        This ensures consistency:
        - MODULE_COMPLETION studies can use Conditional Hazard-Based Sampling with priorities
        - Other trigger types (COURSE_COMPLETION, LEARNPACK_COMPLETION, SYLLABUS_COMPLETION) 
          are independent and don't need cumulative priorities
        
        If you need surveys for different trigger types, create separate studies.
        """
        if not value:
            return value

        # Get all trigger types from the configurations
        trigger_types = set()
        for config in value:
            if config.trigger_type:
                trigger_types.add(config.trigger_type)
            elif config.trigger_type is None:
                # None trigger_type is allowed (for email/list-based studies)
                trigger_types.add(None)

        # If there are multiple different trigger types (excluding None), raise error
        non_null_trigger_types = {t for t in trigger_types if t is not None}

        if len(non_null_trigger_types) > 1:
            trigger_types_str = ", ".join(sorted(non_null_trigger_types))
            raise ValidationException(
                f"All survey configurations in a study must have the same trigger_type. "
                f"Found: {trigger_types_str}. "
                f"Please create separate studies for different trigger types.",
                slug="mixed-trigger-types-in-study"
            )

        return value

class SurveyAnswerSerializer(serializers.Serializer):
    """Serializer for validating survey answers."""

    answers = serializers.DictField(help_text="Dictionary with question IDs as keys and answers as values")

    def validate_answers(self, value):
        """Validate answers format."""
        if not isinstance(value, dict):
            raise ValidationException("answers must be a dictionary", slug="invalid-answers-structure")

        return value

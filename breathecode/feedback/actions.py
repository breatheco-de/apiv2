import json
import logging
import datetime

from capyc.rest_framework.exceptions import ValidationException
from django.contrib.auth.models import User
from django.db import models as django_models
from django.db.models import Avg, Q, QuerySet
from django.utils import timezone

import breathecode.notify.actions as notify_actions
from breathecode.admissions.models import CohortUser
from breathecode.authenticate.models import Token

from . import tasks
from .models import (
    AcademyFeedbackSettings,
    Answer,
    Review,
    ReviewPlatform,
    Survey,
    SurveyConfiguration,
    SurveyStudy,
    SurveyResponse,
)
from .services.pusher_service import send_survey_event
from .utils import strings

logger = logging.getLogger(__name__)


def _update_stats_for_survey_study(survey_study) -> None:
    """Recalculate and persist stats for a SurveyStudy (if present)."""
    if not survey_study:
        return

    qs = SurveyResponse.objects.filter(survey_study=survey_study)
    opened_statuses = [
        SurveyResponse.Status.OPENED,
        SurveyResponse.Status.PARTIAL,
        SurveyResponse.Status.ANSWERED,
    ]
    stats = {
        "sent": qs.count(),
        "opened": qs.filter(Q(opened_at__isnull=False) | Q(status__in=opened_statuses)).count(),
        "partial_responses": qs.filter(status=SurveyResponse.Status.PARTIAL).count(),
        "responses": qs.filter(status=SurveyResponse.Status.ANSWERED).count(),
        "email_opened": qs.filter(email_opened_at__isnull=False).count(),
        "updated_at": timezone.now().isoformat(),
    }

    survey_study.stats = stats
    survey_study.save(update_fields=["stats", "updated_at"])


def update_survey_stats(survey_response: SurveyResponse) -> None:
    """Update stats for related SurveyStudy (SurveyConfiguration does not store stats)."""
    if not survey_response:
        return

    _update_stats_for_survey_study(getattr(survey_response, "survey_study", None))


def send_cohort_survey_group(survey=None, cohort=None):

    if survey is None and cohort is None:
        raise ValidationException("Missing survey or cohort", slug="missing-survey-or-cohort")

    if survey is None:
        survey = Survey(cohort=cohort, lang=cohort.language.lower())

    result = {"success": [], "error": []}
    try:

        if cohort is not None:
            if survey.cohort.id != cohort.id:
                raise ValidationException(
                    "The survey does not match the cohort id", slug="survey-does-not-match-cohort"
                )

        if cohort is None:
            cohort = survey.cohort

        cohort_teacher = CohortUser.objects.filter(cohort=survey.cohort, role="TEACHER")
        if cohort_teacher.count() == 0:
            raise ValidationException(
                "This cohort must have a teacher assigned to be able to survey it",
                400,
                slug="cohort-must-have-teacher-assigned-to-survey",
            )

        ucs = CohortUser.objects.filter(cohort=cohort, role="STUDENT").filter()

        # Get settings once for all answerstemplate_slug
        settings = AcademyFeedbackSettings.objects.filter(academy=cohort.academy).first()
        template_slug = settings.cohort_survey_template.slug if settings and settings.cohort_survey_template else None
        survey.template_slug = template_slug
        survey.save()

        if survey.template_slug is None or not survey.template_slug:
            raise ValidationException(
                "This Academy does not have a template assigned for cohort surveys",
                400,
                slug="no-cohort-survey",
            )

        for uc in ucs:
            if uc.educational_status in ["ACTIVE", "GRADUATED"]:
                tasks.send_cohort_survey.delay(uc.user.id, survey.id, template_slug)

                logger.debug(f"Survey scheduled to send for {uc.user.email}")
                result["success"].append(f"Survey scheduled to send for {uc.user.email}")
            else:
                logger.debug(f"Survey NOT sent to {uc.user.email} because it's not an active or graduated student")
                result["error"].append(
                    f"Survey NOT sent to {uc.user.email} because it's not an active or graduated student"
                )
        survey.sent_at = timezone.now()

        first_answer = Answer.objects.filter(survey=survey).first()
        if first_answer:
            survey.title = first_answer.title or f"Survey {first_answer.id}"

        if len(result["error"]) == 0:
            survey.status = "SENT"
        elif len(result["success"]) > 0 and len(result["error"]) > 0:
            survey.status = "PARTIAL"
        else:
            survey.status = "FATAL"

        survey.status_json = json.dumps(result)
        survey.save()

    except Exception as e:

        survey.status = "FATAL"
        result["error"].append("Error sending survey to group: " + str(e))
        survey.status_json = json.dumps(result)
        survey.save()
        raise e

    return result


def send_question(user, cohort=None):
    answer = Answer(user=user)

    # just can send the question if the user is active in the cohort
    cu_kwargs = {"user": user, "educational_status__in": ["ACTIVE", "GRADUATED"]}
    if cohort:
        cu_kwargs["cohort"] = cohort

    ###1
    cu = CohortUser.objects.filter(**cu_kwargs).order_by("-cohort__kickoff_date").first()
    if not cu:
        raise ValidationException(
            "Impossible to determine the student cohort, maybe it has more than one, or cero.",
            slug="without-cohort-or-cannot-determine-cohort",
        )

    answer.cohort = cu.cohort
    answer.lang = answer.cohort.language.lower()
    answer.save()

    has_slackuser = hasattr(user, "slackuser")

    if not user.email and not has_slackuser:
        raise ValidationException(
            f"User not have email and slack, this survey cannot be send: {str(user.id)}",
            slug="without-email-or-slack-user",
        )

    if not answer.cohort.syllabus_version:
        raise ValidationException("Cohort not have one SyllabusVersion", slug="cohort-without-syllabus-version")

    if not answer.cohort.schedule:
        raise ValidationException("Cohort not have one SyllabusSchedule", slug="cohort-without-specialty-mode")

    question_was_sent_previously = Answer.objects.filter(cohort=answer.cohort, user=user, status="SENT").count()

    # TODO: send custom questions using the survey template slug and test it
    answer = tasks.build_question(answer)

    if question_was_sent_previously:
        answer = Answer.objects.filter(cohort=answer.cohort, user=user, status="SENT").first()
        Token.objects.filter(id=answer.token_id).delete()

    else:
        answer.lang = answer.cohort.language.lower()
        answer.save()

    token, _ = Token.get_or_create(user, token_type="temporal", hours_length=72)
    answer.token_id = token.id
    answer.save()

    data = {
        "QUESTION": answer.title,
        "HIGHEST": answer.highest,
        "LOWEST": answer.lowest,
        "SUBJECT": answer.title,
        "ANSWER_ID": answer.id,
        "BUTTON": strings[answer.cohort.language.lower()]["button_label"],
        "LINK": f"https://nps.4geeks.com/{answer.id}?token={token.key}",
    }

    if user.email:
        notify_actions.send_email_message("nps", user.email, data, academy=answer.cohort.academy)

    if hasattr(user, "slackuser") and hasattr(answer.cohort.academy, "slackteam"):
        notify_actions.send_slack(
            "nps", user.slackuser, answer.cohort.academy.slackteam, data=data, academy=answer.cohort.academy
        )

    # keep track of sent survays until they get answered
    if not question_was_sent_previously:
        logger.info(f"Survey was sent for user: {str(user.id)}")
        answer.status = "SENT"
        answer.save()

    else:
        logger.info(f"Survey was resent for user: {str(user.id)}")

    return True


def answer_survey(user, data):
    Answer.objects.create(**{**data, "user": user})


def get_student_answer_avg(user_id, cohort_id=None, academy_id=None):

    answers = Answer.objects.filter(user__id=user_id, status="ANSWERED", score__isnull=False)

    # optionally filter by cohort
    if cohort_id is not None:
        answers = answers.filter(cohort__id=cohort_id)

    # optionally filter by academy
    if academy_id is not None:
        answers = answers.filter(academy__id=academy_id)

    query = answers.aggregate(average=Avg("score"))

    if query["average"] is not None:
        return round(query["average"], 2)

    return query["average"]


def create_user_graduation_reviews(user, cohort) -> bool:

    # If the user gave us a rating >=8 we should create reviews for each review platform with status "pending"
    average = get_student_answer_avg(user.id, cohort.id)
    if average is None or average >= 8:
        total_reviews = Review.objects.filter(
            cohort=cohort,
            author=user,
        ).count()
        if total_reviews > 0:
            logger.info("No new reviews will be requested, student already has pending requests for this cohort")
            return False

        platforms = ReviewPlatform.objects.all()
        logger.info(f"{platforms.count()} will be requested for student {user.id}, avg NPS score of {average}")
        for plat in platforms:
            review = Review(cohort=cohort, author=user, platform=plat, nps_previous_rating=average)
            review.save()

        return True

    logger.info(f"No reviews requested for student {user.id} because average NPS score is {average}")
    return False


def calculate_survey_response_rate(survey_id: int) -> float:
    total_responses = Answer.objects.filter(survey__id=survey_id).count()
    answered_responses = Answer.objects.filter(survey__id=survey_id, status="ANSWERED").count()
    response_rate = (answered_responses / total_responses) * 100

    return response_rate


def calculate_survey_scores(survey_id: int) -> dict:

    def get_average(answers: QuerySet[Answer]) -> float:
        result = answers.aggregate(Avg("score"))
        return result["score__avg"]

    survey = Survey.objects.filter(id=survey_id).first()
    if not survey:
        raise ValidationException("Survey not found", code=404, slug="not-found")

    answers = Answer.objects.filter(survey=survey, status="ANSWERED")
    total = get_average(answers)

    # Get academy answers - answers that have academy field set but no mentor, cohort, or live_class
    academy = get_average(
        answers.filter(
            academy__isnull=False,
            mentor__isnull=True,
            cohort__isnull=True,
            live_class__isnull=True,
            mentorship_session__isnull=True,
        )
    )

    # Get cohort answers - answers that have cohort field set but no mentor or live_class
    cohort = get_average(
        answers.filter(
            cohort__isnull=False, mentor__isnull=True, live_class__isnull=True, mentorship_session__isnull=True
        )
    )

    # Get live class answers - answers that have live_class field set
    live_class = get_average(answers.filter(live_class__isnull=False))

    # Get mentor answers - combining both direct assignments and mentorship sessions
    mentor_answers = answers.filter(Q(mentor__isnull=False) | Q(mentorship_session__isnull=False))

    # Get unique mentors from both direct assignments and mentorship sessions
    mentor_ids = set()
    mentor_ids.update(mentor_answers.values_list("mentor_id", flat=True).distinct())
    mentor_ids.update(
        mentor_answers.filter(mentorship_session__isnull=False)
        .values_list("mentorship_session__mentor__user_id", flat=True)
        .distinct()
    )
    mentor_ids.discard(None)  # Remove None values if any

    mentors = []
    for mentor in User.objects.filter(id__in=mentor_ids):
        # Calculate average score for this mentor combining both types of answers
        mentor_score = get_average(mentor_answers.filter(Q(mentor=mentor) | Q(mentorship_session__mentor__user=mentor)))
        if mentor_score is not None:
            mentors.append({"name": f"{mentor.first_name} {mentor.last_name}", "score": mentor_score})

    return {
        "total": total,
        "academy": academy,
        "cohort": cohort,
        "live_class": live_class,
        "mentors": sorted(mentors, key=lambda x: x["name"]),
    }


def trigger_survey_for_user(user: User, trigger_type: str, context: dict):
    """
    Trigger a survey for a user when a specific action is completed.

    Args:
        user: User who completed the action
        trigger_type: Type of trigger (must be one of SurveyConfiguration.TriggerType values)
        context: Context information about the trigger (e.g., {"asset_slug": "...", "cohort": ...})

    Returns:
        SurveyResponse instance if created, None otherwise
    """
    if context is None:
        context = {}

    if not user:
        logger.warning("[survey-trigger] abort: user is None | trigger_type=%s", trigger_type)
        return None

    # Validate trigger_type
    valid_triggers = [choice[0] for choice in SurveyConfiguration.TriggerType.choices]
    if trigger_type not in valid_triggers:
        logger.warning(
            "[survey-trigger] abort: invalid trigger_type=%s valid_triggers=%s user_id=%s",
            trigger_type,
            valid_triggers,
            user.id,
        )
        return None

    logger.info(
        "[survey-trigger] start | user_id=%s trigger_type=%s context_keys=%s",
        user.id,
        trigger_type,
        sorted(list(context.keys())),
    )

    # Get academy for filtering SurveyConfiguration.
    # Prefer explicit context academy (e.g. cohort.academy) because users can belong to multiple academies.
    academy = None
    academy_source = None
    if "academy" in context and context["academy"] is not None:
        academy = context["academy"]
        academy_source = "context"
    elif hasattr(user, "profileacademy_set") and user.profileacademy_set.exists():
        academy = user.profileacademy_set.first().academy
        academy_source = "profileacademy_set.first"

    if not academy:
        logger.warning(
            "[survey-trigger] abort: no academy found | user_id=%s trigger_type=%s has_profileacademy=%s context_has_academy=%s",
            user.id,
            trigger_type,
            bool(getattr(user, "profileacademy_set", None) and user.profileacademy_set.exists()),
            "academy" in context,
        )
        return None
    else:
        logger.info(
            "[survey-trigger] academy resolved | user_id=%s academy_id=%s source=%s",
            user.id,
            academy.id,
            academy_source,
        )

    # Find active survey configurations for this trigger type and academy
    # Use prefetch_related to avoid N+1 queries when checking cohorts
    survey_configs = SurveyConfiguration.objects.filter(
        trigger_type=trigger_type, is_active=True, academy=academy
    ).prefetch_related("cohorts")

    if not survey_configs.exists():
        logger.info(
            "[survey-trigger] no active configs | user_id=%s trigger_type=%s academy_id=%s",
            user.id,
            trigger_type,
            academy.id,
        )
        return None

    # Apply filters for each survey configuration
    filtered_out = 0
    for survey_config in survey_configs:
        # Study gate: only trigger realtime surveys when there is an active SurveyStudy that includes this config.
        utc_now = timezone.now()
        active_study = (
            SurveyStudy.objects.filter(
                academy=academy,
                survey_configurations=survey_config,
            )
            .filter(Q(starts_at__lte=utc_now) | Q(starts_at__isnull=True))
            .filter(Q(ends_at__gte=utc_now) | Q(ends_at__isnull=True))
            .order_by("-starts_at", "-id")
            .first()
        )

        if not active_study:
            logger.info(
                "[survey-trigger] skip: no active study | user_id=%s survey_config_id=%s trigger_type=%s academy_id=%s",
                user.id,
                survey_config.id,
                trigger_type,
                academy.id,
            )
            continue

        # Apply cohort filter for course completion
        if trigger_type == SurveyConfiguration.TriggerType.COURSE_COMPLETION:
            cohort = context.get("cohort")
            if cohort:
                # If cohorts filter is set, check if this cohort is in the list
                if survey_config.cohorts.exists():
                    if cohort not in survey_config.cohorts.all():
                        filtered_out += 1
                        logger.info(
                            "[survey-trigger] filtered by cohort | user_id=%s survey_config_id=%s cohort_id=%s academy_id=%s",
                            user.id,
                            survey_config.id,
                            getattr(cohort, "id", None),
                            academy.id,
                        )
                        continue
                # If cohorts filter is empty, apply to all cohorts

        # Apply asset_slug filter for learnpack completion
        elif trigger_type == SurveyConfiguration.TriggerType.LEARNPACK_COMPLETION:
            asset_slug = context.get("asset_slug")
            if asset_slug:
                # If asset_slugs filter is set, check if this asset_slug is in the list
                if survey_config.asset_slugs:
                    if asset_slug not in survey_config.asset_slugs:
                        filtered_out += 1
                        logger.info(
                            "[survey-trigger] filtered by asset_slug | user_id=%s survey_config_id=%s asset_slug=%s academy_id=%s",
                            user.id,
                            survey_config.id,
                            asset_slug,
                            academy.id,
                        )
                        continue
                # If asset_slugs filter is empty, apply to all learnpacks

        # Check if user already has a response for this config+trigger (avoid re-asking the same survey).
        dedupe_query = SurveyResponse.objects.filter(
            survey_config=survey_config,
            user=user,
            survey_study=active_study,
            trigger_context__trigger_type=trigger_type,
        ).exclude(status=SurveyResponse.Status.EXPIRED)

        if trigger_type == SurveyConfiguration.TriggerType.COURSE_COMPLETION:
            cohort_id = context.get("cohort_id")
            cohort = context.get("cohort")
            if cohort_id is None and cohort is not None:
                cohort_id = getattr(cohort, "id", None)

            if cohort_id is not None:
                dedupe_query = dedupe_query.filter(trigger_context__cohort_id=cohort_id)

        existing_response = dedupe_query.first()

        if existing_response:
            logger.info(
                "[survey-trigger] skip: existing response | user_id=%s survey_config_id=%s survey_response_id=%s status=%s",
                user.id,
                survey_config.id,
                existing_response.id,
                existing_response.status,
            )
            continue

        # Create survey response
        survey_response = create_survey_response(survey_config, user, context, survey_study=active_study)
        if survey_response:
            logger.info(
                "[survey-trigger] created | user_id=%s survey_config_id=%s survey_study_id=%s survey_response_id=%s",
                user.id,
                survey_config.id,
                active_study.id,
                survey_response.id,
            )
            return survey_response

    logger.info(
        "[survey-trigger] no response created | user_id=%s trigger_type=%s academy_id=%s configs=%s filtered_out=%s",
        user.id,
        trigger_type,
        academy.id,
        survey_configs.count(),
        filtered_out,
    )
    return None


def create_survey_response(
    survey_config: SurveyConfiguration, user: User, context: dict, survey_study: SurveyStudy | None = None
):
    """
    Create a survey response and send Pusher event.

    Args:
        survey_config: SurveyConfiguration instance
        user: User who should receive the survey
        context: Context information about the trigger

    Returns:
        SurveyResponse instance if created successfully, None otherwise
    """
    try:
        if context is None:
            context = {}

        logger.info(
            "[survey-response] start | user_id=%s survey_config_id=%s academy_id=%s trigger_type=%s context_keys=%s",
            getattr(user, "id", None),
            getattr(survey_config, "id", None),
            getattr(getattr(survey_config, "academy", None), "id", None),
            getattr(survey_config, "trigger_type", None),
            sorted(list(context.keys())),
        )

        def _serialize_trigger_context(value):
            """
            Convert values into JSON-serializable shapes for storage in JSONField.

            `context` can include Django model instances for filtering, but the stored `trigger_context`
            must be JSON-serializable.
            """
            if value is None:
                return None

            if isinstance(value, django_models.Model):
                payload = {"id": value.pk, "model": value._meta.label_lower}
                if hasattr(value, "slug"):
                    payload["slug"] = getattr(value, "slug")
                return payload

            if isinstance(value, (datetime.datetime, datetime.date)):
                return value.isoformat()

            if isinstance(value, (str, int, float, bool)):
                return value

            if isinstance(value, dict):
                return {str(k): _serialize_trigger_context(v) for k, v in value.items()}

            if isinstance(value, list):
                return [_serialize_trigger_context(v) for v in value]

            return str(value)

        # Prepare trigger context
        trigger_context = {
            "trigger_type": survey_config.trigger_type,
            **_serialize_trigger_context(context),
        }

        # Create survey response
        questions_snapshot = survey_config.questions
        survey_response = SurveyResponse.objects.create(
            survey_config=survey_config,
            survey_study=survey_study,
            user=user,
            trigger_context=trigger_context,
            questions_snapshot=questions_snapshot,
            status=SurveyResponse.Status.PENDING,
        )

        logger.info(
            "[survey-response] created | user_id=%s survey_response_id=%s survey_config_id=%s",
            user.id,
            survey_response.id,
            survey_config.id,
        )

        # Update aggregated stats (best-effort)
        try:
            update_survey_stats(survey_response)
        except Exception:
            logger.exception("[survey-response] unable to update stats after create")

        # Send Pusher event
        questions = (questions_snapshot or {}).get("questions", [])
        send_survey_event(user.id, survey_response.id, questions, trigger_context)

        logger.info(
            "[survey-response] pusher sent | user_id=%s survey_response_id=%s questions=%s",
            user.id,
            survey_response.id,
            len(questions) if isinstance(questions, list) else None,
        )
        return survey_response

    except Exception as e:
        logger.error(
            "[survey-response] error | user_id=%s survey_config_id=%s error=%s",
            getattr(user, "id", None),
            getattr(survey_config, "id", None),
            str(e),
            exc_info=True,
        )
        return None


def save_survey_answers(response_id: int, answers: dict) -> SurveyResponse:
    """
    Save survey answers and update response status.

    Args:
        response_id: ID of the SurveyResponse
        answers: Dictionary with question IDs as keys and answers as values

    Returns:
        Updated SurveyResponse instance

    Raises:
        ValidationException: If response not found, already answered, or validation fails
    """
    from django.db import transaction

    # Use select_for_update to prevent race conditions
    with transaction.atomic():
        survey_response = SurveyResponse.objects.select_for_update().filter(id=response_id).first()

        if not survey_response:
            raise ValidationException("Survey response not found", code=404, slug="survey-response-not-found")

        if survey_response.status == SurveyResponse.Status.ANSWERED:
            raise ValidationException("Survey already answered", code=400, slug="survey-already-answered")

        # Validate answers against survey configuration
        questions = survey_response.survey_config.questions.get("questions", [])
        question_ids = {q.get("id") for q in questions if q.get("id")}

        # Check if all required questions are answered
        for question in questions:
            question_id = question.get("id")
            if question_id and question_id not in answers:
                # Check if question is required
                if question.get("required", False):
                    raise ValidationException(
                        f"Required question '{question_id}' not answered", code=400, slug="missing-required-question"
                    )

        # Validate answer types and values
        for question_id, answer_value in answers.items():
            if question_id not in question_ids:
                logger.warning(f"Answer for unknown question '{question_id}' will be saved but not validated")

            # Find question config
            question = next((q for q in questions if q.get("id") == question_id), None)
            if question:
                question_type = question.get("type")
                config = question.get("config", {})

                # Validate based on question type
                if question_type == "likert_scale":
                    scale = config.get("scale", 5)
                    if not isinstance(answer_value, int) or answer_value < 1 or answer_value > scale:
                        raise ValidationException(
                            f"Answer for '{question_id}' must be an integer between 1 and {scale}",
                            code=400,
                            slug="invalid-likert-answer",
                        )

                elif question_type == "open_question":
                    max_length = config.get("max_length", 500)
                    if not isinstance(answer_value, str):
                        raise ValidationException(
                            f"Answer for '{question_id}' must be a string", code=400, slug="invalid-open-answer-type"
                        )
                    if len(answer_value) > max_length:
                        raise ValidationException(
                            f"Answer for '{question_id}' exceeds maximum length of {max_length} characters",
                            code=400,
                            slug="answer-too-long",
                        )

        # Save answers
        survey_response.answers = answers
        survey_response.status = SurveyResponse.Status.ANSWERED
        survey_response.answered_at = timezone.now()
        survey_response.save()

    # Trigger signal for webhook
    from breathecode.feedback.signals import survey_response_answered

    survey_response_answered.send(sender=SurveyResponse, instance=survey_response)

    try:
        update_survey_stats(survey_response)
    except Exception:
        logger.exception("[survey-response] unable to update stats after answered")

    logger.info(f"Survey response {survey_response.id} answered by user {survey_response.user.id}")
    return survey_response

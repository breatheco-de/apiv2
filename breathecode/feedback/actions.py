import datetime
import json
import logging

from capyc.rest_framework.exceptions import ValidationException
from django.contrib.auth.models import User
from django.db import models as django_models
from django.db.models import Avg, Q, QuerySet
from django.utils import timezone

import breathecode.notify.actions as notify_actions
from breathecode.admissions.models import Cohort, CohortUser, SyllabusVersion
from breathecode.assignments.models import Task
from breathecode.authenticate.models import Token
from breathecode.certificate.actions import syllabus_weeks_to_days

from . import tasks
from .models import (
    AcademyFeedbackSettings,
    Answer,
    Review,
    ReviewPlatform,
    Survey,
    SurveyConfiguration,
    SurveyResponse,
    SurveyStudy,
)
from .services.pusher_service import send_survey_event
from .utils import strings
from .utils.survey_manager import SurveyManager

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
    answer.academy = answer.cohort.academy
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


def _find_module_for_asset_in_syllabus(syllabus_version: SyllabusVersion, asset_slug: str) -> int | None:
    """
    Find the module index (0-based) where an asset_slug appears in a syllabus_version.

    Returns:
        Module index (int) if found, None otherwise.
    """
    if not syllabus_version or not syllabus_version.json:
        return None

    if isinstance(syllabus_version.json, str):
        syllabus_json = json.loads(syllabus_version.json)
    else:
        syllabus_json = syllabus_version.json

    syllabus_json = syllabus_weeks_to_days(syllabus_json)

    key_map = {
        "QUIZ": "quizzes",
        "LESSON": "lessons",
        "EXERCISE": "replits",
        "PROJECT": "assignments",
    }

    for module_index, day in enumerate(syllabus_json.get("days", [])):
        for atype, day_key in key_map.items():
            if day_key not in day:
                continue

            for asset in day[day_key]:
                asset_slug_in_day = asset.get("slug") if isinstance(asset, dict) else asset
                if asset_slug_in_day == asset_slug:
                    return module_index

    return None


def _get_module_assets_from_syllabus(syllabus_version: SyllabusVersion, module_index: int) -> list[str]:
    """
    Get all asset slugs (learnpacks) from a specific module in a syllabus_version.

    Returns:
        List of asset slugs (strings).
    """
    if not syllabus_version or not syllabus_version.json:
        return []

    if isinstance(syllabus_version.json, str):
        syllabus_json = json.loads(syllabus_version.json)
    else:
        syllabus_json = syllabus_version.json

    syllabus_json = syllabus_weeks_to_days(syllabus_json)

    days = syllabus_json.get("days", [])
    if module_index < 0 or module_index >= len(days):
        return []

    day = days[module_index]
    key_map = {
        "QUIZ": "quizzes",
        "LESSON": "lessons",
        "EXERCISE": "replits",
        "PROJECT": "assignments",
    }

    assets = []
    for atype, day_key in key_map.items():
        if day_key not in day:
            continue

        for asset in day[day_key]:
            asset_slug = asset.get("slug") if isinstance(asset, dict) else asset
            if asset_slug:
                assets.append(asset_slug)

    return assets


def _is_module_complete(user: User, cohort: Cohort, module_index: int) -> bool:
    """
    Check if a user has completed all learnpacks in a specific module of their cohort's syllabus.

    Returns:
        True if all learnpacks in the module are DONE, False otherwise.
    """
    if not cohort or not cohort.syllabus_version:
        return False

    module_assets = _get_module_assets_from_syllabus(cohort.syllabus_version, module_index)
    if not module_assets:
        return False

    # Check if all assets in this module have at least one DONE task for this user in this cohort
    for asset_slug in module_assets:
        has_done_task = Task.objects.filter(
            user=user,
            cohort=cohort,
            associated_slug=asset_slug,
            task_status=Task.TaskStatus.DONE,
        ).exists()

        if not has_done_task:
            return False

    return True


def _is_syllabus_complete(user: User, cohort: Cohort) -> bool:
    """
    Check if a user has completed all modules in their cohort's syllabus.

    Returns:
        True if all modules are complete, False otherwise.
    """
    if not cohort or not cohort.syllabus_version:
        return False

    if isinstance(cohort.syllabus_version.json, str):
        syllabus_json = json.loads(cohort.syllabus_version.json)
    else:
        syllabus_json = cohort.syllabus_version.json

    syllabus_json = syllabus_weeks_to_days(syllabus_json)
    total_modules = len(syllabus_json.get("days", []))

    if total_modules == 0:
        return False

    # Check if all modules are complete
    for module_index in range(total_modules):
        if not _is_module_complete(user, cohort, module_index):
            return False

    return True


def has_active_survey_studies(academy, trigger_types: list[str] | str) -> bool:
    """
    Check if there are any active SurveyStudy instances for the given academy and trigger types.

    Args:
        academy: Academy instance to check
        trigger_types: Single trigger type string or list of trigger type strings

    Returns:
        True if there is at least one active study with the specified trigger types, False otherwise
    """
    if not academy:
        return False

    if isinstance(trigger_types, str):
        trigger_types = [trigger_types]

    utc_now = timezone.now()
    active_studies = (
        SurveyStudy.objects.filter(
            academy=academy,
            survey_configurations__trigger_type__in=trigger_types,
            survey_configurations__is_active=True,
        )
        .filter(Q(starts_at__lte=utc_now) | Q(starts_at__isnull=True))
        .filter(Q(ends_at__gte=utc_now) | Q(ends_at__isnull=True))
        .distinct()
        .exists()
    )

    return active_studies


def trigger_survey_for_user(user: User, trigger_type: str, context: dict):
    """
    Trigger a survey for a user when a specific action is completed.

    This is a convenience wrapper around SurveyManager for backward compatibility.

    Args:
        user: User who completed the action
        trigger_type: Type of trigger (must be one of SurveyConfiguration.TriggerType values)
        context: Context information about the trigger (e.g., {"asset_slug": "...", "cohort": ...})

    Returns:
        SurveyResponse instance if created, None otherwise
    """
    manager = SurveyManager(user, trigger_type, context)
    return manager.trigger_survey_for_user()


def create_survey_response(
    survey_config: SurveyConfiguration,
    user: User,
    context: dict,
    survey_study: SurveyStudy | None = None,
    send_pusher: bool = True,
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

        if send_pusher:
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

import json
import logging

from capyc.rest_framework.exceptions import ValidationException
from django.contrib.auth.models import User
from django.db.models import Avg, Q, QuerySet
from django.utils import timezone

import breathecode.notify.actions as notify_actions
from breathecode.admissions.models import CohortUser
from breathecode.authenticate.models import Token

from . import tasks
from .models import AcademyFeedbackSettings, Answer, Review, ReviewPlatform, Survey
from .utils import strings

logger = logging.getLogger(__name__)


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

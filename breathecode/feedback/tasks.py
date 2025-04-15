import os
from datetime import datetime, timedelta

from capyc.rest_framework.exceptions import ValidationException
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from django_redis import get_redis_connection
from redis.exceptions import LockError
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

from breathecode.admissions.models import Cohort, CohortUser
from breathecode.authenticate.models import Token
from breathecode.events.models import Event, EventCheckin, LiveClass
from breathecode.mentorship.models import MentorshipSession
from breathecode.notify import actions as notify_actions
from breathecode.utils import TaskPriority, getLogger
from breathecode.utils.redis import Lock

from . import actions
from .models import AcademyFeedbackSettings, Answer, Survey, SurveyTemplate
from .utils import strings

# Get an instance of a logger
logger = getLogger(__name__)

ADMIN_URL = os.getenv("ADMIN_URL", "")
API_URL = os.getenv("API_URL", "")
ENV = os.getenv("ENV", "")
IS_DJANGO_REDIS = hasattr(cache, "fake") is False


def build_question(answer, surveytemplate_slug=None):
    """Build question details from SurveyTemplate based on answer type and update the answer object"""
    lang = answer.lang.lower()
    academy = None

    # Determine which academy to use
    if answer.academy:
        academy = answer.academy
    elif answer.cohort:
        academy = answer.cohort.academy
    elif answer.mentorship_session:
        academy = answer.mentorship_session.mentor.academy
    elif answer.event:
        academy = answer.event.academy
    elif answer.live_class and answer.live_class.cohort_time_slot:
        academy = answer.live_class.cohort_time_slot.cohort.academy

    # Get academy settings if they exist
    settings = None
    if academy:
        settings = AcademyFeedbackSettings.objects.filter(academy=academy).first()

    # If we have settings, try to get the appropriate template
    template = None
    if settings:
        if answer.mentorship_session is not None:
            template = settings.mentorship_session_survey_template
        elif answer.event is not None:
            template = settings.event_survey_template
        elif answer.live_class is not None:
            template = settings.liveclass_survey_template
        elif answer.cohort is not None:
            template = settings.cohort_survey_template

    # If no template from settings, try finding it by slug
    if template is None:
        template = SurveyTemplate.get_template(slug=surveytemplate_slug, lang=lang, academy=academy)

    if template is None:
        raise ValidationException(
            f"No survey template found for language {lang}"
            + (f" and slug {surveytemplate_slug}" if surveytemplate_slug else "")
        )

    if answer.question_by_slug is not None and answer.question_by_slug != "":
        # Check additional questions first
        if template.additional_questions and answer.question_by_slug in template.additional_questions:
            q = template.additional_questions[answer.question_by_slug]
            answer.title = q["title"]
            answer.lowest = q["lowest"]
            answer.highest = q["highest"]
        # Then check if it matches any of the standard question fields
        elif hasattr(template, f"when_asking_{answer.question_by_slug.lower()}"):
            q = getattr(template, f"when_asking_{answer.question_by_slug.lower()}")
            answer.title = q["title"]
            answer.lowest = q["lowest"]
            answer.highest = q["highest"]

    elif answer.mentorship_session is not None:
        if template.when_asking_mentorshipsession:
            q = template.when_asking_mentorshipsession
            answer.title = q["title"]
            answer.lowest = q["lowest"]
            answer.highest = q["highest"]
            # Format mentor name into title
            if "{}" in answer.title:
                answer.title = answer.title.format(
                    f"{answer.mentorship_session.mentor.user.first_name} {answer.mentorship_session.mentor.user.last_name}"
                )

    elif answer.event is not None:
        if template.when_asking_event:
            answer.title = template.when_asking_event["title"]
            answer.lowest = template.when_asking_event["lowest"]
            answer.highest = template.when_asking_event["highest"]

    elif answer.live_class is not None:
        if template.when_asking_liveclass_mentor:
            answer.title = template.when_asking_liveclass_mentor["title"]
            answer.lowest = template.when_asking_liveclass_mentor["lowest"]
            answer.highest = template.when_asking_liveclass_mentor["highest"]

    elif answer.mentor is not None:
        if template.when_asking_mentor:
            q = template.when_asking_mentor
            answer.title = q["title"]
            answer.lowest = q["lowest"]
            answer.highest = q["highest"]
            # Format mentor name into title
            if "{}" in answer.title:
                answer.title = answer.title.format(answer.mentor.first_name + " " + answer.mentor.last_name)

    elif answer.cohort is not None:
        if template.when_asking_cohort:
            q = template.when_asking_cohort
            answer.title = q["title"]
            answer.lowest = q["lowest"]
            answer.highest = q["highest"]
            # Format cohort name into title
            if "{}" in answer.title:
                title = (
                    answer.cohort.syllabus_version.syllabus.name
                    if answer.cohort.syllabus_version and answer.cohort.syllabus_version.syllabus.name
                    else answer.cohort.name
                )
                answer.title = answer.title.format(title)

    elif answer.academy is not None:
        if template.when_asking_academy:
            q = template.when_asking_academy
            answer.title = q["title"]
            answer.lowest = q["lowest"]
            answer.highest = q["highest"]
            # Format academy name into title
            if "{}" in answer.title:
                answer.title = answer.title.format(answer.academy.name)

    return answer


def get_system_email():
    system_email = os.getenv("SYSTEM_EMAIL")
    return system_email


def get_admin_url():
    admin_url = os.getenv("ADMIN_URL")
    return admin_url


def generate_user_cohort_survey_answers(user, survey, status="OPENED", template_slug=None):

    if not CohortUser.objects.filter(
        cohort=survey.cohort, role="STUDENT", user=user, educational_status__in=["ACTIVE", "GRADUATED"]
    ).exists():
        raise ValidationException("This student does not belong to this cohort", 400)

    cohort_teacher = CohortUser.objects.filter(
        cohort=survey.cohort, role="TEACHER", educational_status__in=["ACTIVE", "GRADUATED"]
    )
    if cohort_teacher.count() == 0:
        raise ValidationException("This cohort must have a teacher assigned to be able to survey it", 400)

    if template_slug is None:
        raise ValidationException("Template slug must be specified before building the question", 500)

    def new_answer(answer: Answer):
        answer = build_question(answer, template_slug)
        answer.user = user
        answer.status = status
        answer.survey = survey
        answer.opened_at = timezone.now()
        answer.save()
        return answer

    _answers = Answer.objects.filter(survey__id=survey.id, user=user)
    if _answers.count() == 0:
        _answers = []

        # ask for the cohort in general
        answer = Answer(cohort=survey.cohort, academy=survey.cohort.academy, lang=survey.lang)
        _answers.append(new_answer(answer))

        if survey.cohort.available_as_saas is False or (
            survey.cohort.available_as_saas is None and survey.cohort.academy.available_as_saas is False
        ):
            # ask for each teacher, with a max of 2 teachers
            count = 0
            for ct in cohort_teacher:
                if count >= survey.max_teachers_to_ask:
                    break
                answer = Answer(mentor=ct.user, cohort=survey.cohort, academy=survey.cohort.academy, lang=survey.lang)
                _answers.append(new_answer(answer))
                count = count + 1

            # ask for the first TA
            cohort_assistant = CohortUser.objects.filter(
                cohort=survey.cohort, role="ASSISTANT", educational_status__in=["ACTIVE", "GRADUATED"]
            )
            count = 0
            for ca in cohort_assistant:
                if count >= survey.max_assistants_to_ask:
                    break
                answer = Answer(mentor=ca.user, cohort=survey.cohort, academy=survey.cohort.academy, lang=survey.lang)
                _answers.append(new_answer(answer))
                count = count + 1

        # ask for the whole academy
        answer = Answer(academy=survey.cohort.academy, lang=survey.lang)
        _answers.append(new_answer(answer))

        # ask for the platform and the content
        answer = Answer(question_by_slug="PLATFORM", lang=survey.lang)
        _answers.append(new_answer(answer))

    return _answers


def api_url():
    return os.getenv("API_URL", "")


@task(bind=False, priority=TaskPriority.NOTIFICATION.value)
def send_cohort_survey(user_id, survey_id, template_slug=None, **_):
    logger.info("Starting send_cohort_survey")
    survey = Survey.objects.filter(id=survey_id).first()
    if survey is None:
        raise RetryTask("Survey not found")

    user = User.objects.filter(id=user_id).first()
    if user is None:
        raise AbortTask("User not found")

    utc_now = timezone.now()

    if utc_now > survey.created_at + survey.duration:
        raise AbortTask("This survey has already expired")

    cu = CohortUser.objects.filter(
        cohort=survey.cohort, role="STUDENT", user=user, educational_status__in=["ACTIVE", "GRADUATED"]
    ).first()
    if cu is None:
        raise AbortTask("This student does not belong to this cohort")

    try:
        generate_user_cohort_survey_answers(user, survey, status="SENT", template_slug=template_slug)

    except Exception as e:
        raise AbortTask(str(e))

    has_slackuser = hasattr(user, "slackuser")
    if not user.email and not has_slackuser:
        message = f"Author not have email and slack, this survey cannot be send by {str(user.id)}"
        raise AbortTask(message)

    token, created = Token.get_or_create(user, token_type="temporal", hours_length=48)
    data = {
        "SUBJECT": strings[survey.lang]["survey_subject"],
        "MESSAGE": strings[survey.lang]["survey_message"],
        "TRACKER_URL": f"{api_url()}/v1/feedback/survey/{survey_id}/tracker.png",
        "BUTTON": strings[survey.lang]["button_label"],
        "LINK": f"https://nps.4geeks.com/survey/{survey_id}?token={token.key}",
    }

    if user.email:
        notify_actions.send_email_message("nps_survey", user.email, data, academy=survey.cohort.academy)

    if hasattr(user, "slackuser") and hasattr(survey.cohort.academy, "slackteam"):
        notify_actions.send_slack(
            "nps_survey", user.slackuser, survey.cohort.academy.slackteam, data=data, academy=survey.cohort.academy
        )


@task(bind=False, priority=TaskPriority.ACADEMY.value)
def process_student_graduation(cohort_id, user_id, **_):
    from .actions import create_user_graduation_reviews

    logger.debug("Starting process_student_graduation")

    cohort = Cohort.objects.filter(id=cohort_id).first()
    if cohort is None:
        raise AbortTask(f"Invalid cohort id: {cohort_id}")

    user = User.objects.filter(id=user_id).first()
    if user is None:
        raise AbortTask(f"Invalid user id: {user_id}")

    create_user_graduation_reviews(user, cohort)


@task(bind=False, priority=TaskPriority.ACADEMY.value)
def recalculate_survey_scores(survey_id, **_):
    logger.info("Starting recalculate_survey_score")

    survey = Survey.objects.filter(id=survey_id).first()
    if survey is None:
        raise RetryTask("Survey not found")

    survey.response_rate = actions.calculate_survey_response_rate(survey.id)
    survey.scores = actions.calculate_survey_scores(survey.id)
    survey.save()


@task(bind=False, priority=TaskPriority.ACADEMY.value)
def process_answer_received(answer_id, **_):
    """
    This task will be called every time a single NPS answer is received
    the task will review the score, if we got less than 7 it will notify
    the school.
    """

    logger.debug("Starting notify_bad_nps_score")
    answer = Answer.objects.filter(id=answer_id).first()
    if answer is None:
        raise RetryTask("Answer not found")

    if answer.survey is None:
        raise AbortTask("No survey connected to answer.")

    answer.survey.response_rate = actions.calculate_survey_response_rate(answer.survey.id)
    answer.survey.scores = actions.calculate_survey_scores(answer.survey.id)
    answer.survey.save()

    if answer.user and answer.academy and answer.score is not None and answer.score < 8:
        system_email = get_system_email()
        admin_url = get_admin_url()
        list_of_emails = []

        if system_email is not None:
            list_of_emails.append(system_email)

        if answer.academy.feedback_email is not None:
            list_of_emails.append(answer.academy.feedback_email)

        if len(list_of_emails) == 0:
            raise AbortTask("No email found.")

        # TODO: instead of sending, use notifications system to be built on the breathecode.admin app.
        if list_of_emails:
            notify_actions.send_email_message(
                "negative_answer",
                list_of_emails,
                data={
                    "SUBJECT": f"A student answered with a bad NPS score at {answer.academy.name}",
                    "FULL_NAME": answer.user.first_name + " " + answer.user.last_name,
                    "QUESTION": answer.title,
                    "SCORE": answer.score,
                    "COMMENTS": answer.comment,
                    "ACADEMY": answer.academy.name,
                    "LINK": f"{admin_url}/feedback/surveys/{answer.academy.slug}/{answer.survey.id}",
                },
                academy=answer.academy,
            )

    return True


@task(bind=False, priority=TaskPriority.NOTIFICATION.value)
def send_mentorship_session_survey(session_id, **_):
    logger.info("Starting send_mentorship_session_survey")
    session = MentorshipSession.objects.filter(id=session_id).first()
    if session is None:
        raise RetryTask("Mentoring session doesn't found")

    if session.mentee is None:
        raise AbortTask("This session doesn't have a mentee")

    if not session.started_at or not session.ended_at:
        raise AbortTask("This session hasn't finished")

    if session.ended_at - session.started_at <= timedelta(minutes=5):
        raise AbortTask("Mentorship session duration is less or equal than five minutes")

    if not session.service:
        raise AbortTask("Mentorship session doesn't have a service associated with it")

    client = None
    if IS_DJANGO_REDIS:
        client = get_redis_connection("default")

    # Get settings once before the lock
    settings = AcademyFeedbackSettings.objects.filter(academy=session.mentor.academy).first()
    template_slug = (
        settings.mentorship_session_survey_template.slug
        if settings and settings.mentorship_session_survey_template
        else None
    )

    try:
        with Lock(client, f"lock:session:{session.id}:answer", timeout=30, blocking_timeout=30):
            answer = Answer.objects.filter(mentorship_session__id=session.id).first()
            if answer is None:
                answer = Answer(
                    mentorship_session=session, academy=session.mentor.academy, lang=session.service.language
                )
                answer = build_question(answer, template_slug)
                answer.user = session.mentee
                answer.status = "SENT"
                answer.save()

            elif answer.status == "ANSWERED":
                raise AbortTask(f"This survey about MentorshipSession {session.id} was answered")

    except LockError:
        raise RetryTask("Could not acquire lock for activity, operation timed out.")

    if not session.mentee.email:
        message = f"Author not have email, this survey cannot be send by {session.mentee.id}"
        raise AbortTask(message)

    token, _ = Token.get_or_create(session.mentee, token_type="temporal", hours_length=48)

    if answer.token_id != token.id:
        answer.token_id = token.id
        answer.save()

    # lazyload api url in test environment
    api_url = API_URL if ENV != "test" else os.getenv("API_URL", "")
    data = {
        "SUBJECT": strings[answer.lang.lower()]["survey_subject"],
        "MESSAGE": answer.title,
        "TRACKER_URL": f"{api_url}/v1/feedback/answer/{answer.id}/tracker.png",
        "BUTTON": strings[answer.lang.lower()]["button_label"],
        "LINK": f"https://nps.4geeks.com/{answer.id}?token={token.key}",
    }

    if session.mentee.email:
        if notify_actions.send_email_message("nps_survey", session.mentee.email, data, academy=session.mentor.academy):
            answer.sent_at = timezone.now()
            answer.save()


@task(bind=False, priority=TaskPriority.NOTIFICATION.value)
def send_event_survey(event_id, **_):
    logger.info("Starting event survey")
    event = Event.objects.filter(id=event_id).first()
    if event is None:
        raise RetryTask("Event not found")

    if not event.ended_at:
        raise AbortTask("This event hasn't finished")

    if Answer.objects.filter(event__id=event.id).exists():
        raise AbortTask("There is already a survey for this event")

    try:
        # Get settings once for all answers
        settings = AcademyFeedbackSettings.objects.filter(academy=event.academy).first()
        template_slug = settings.event_survey_template.slug if settings and settings.event_survey_template else None

        checkins = EventCheckin.objects.filter(event=event, attended_at__isnull=False, attendee__isnull=False)
        for checkin in checkins:
            answer = Answer(event=event, user=checkin.attendee, status="SENT", lang=event.lang, academy=event.academy)
            answer = build_question(answer, template_slug)
            answer.save()

            token, _ = Token.get_or_create(answer.user, token_type="temporal", hours_length=48)

            # lazyload api url in test environment
            api_url = API_URL if ENV != "test" else os.getenv("API_URL", "")
            data = {
                "SUBJECT": answer.title,
                "MESSAGE": answer.title,
                "TRACKER_URL": f"{api_url}/v1/feedback/answer/{answer.id}/tracker.png",
                "BUTTON": strings[answer.lang.lower()]["button_label"],
                "LINK": f"https://nps.4geeks.com/{answer.id}?token={token.key}",
            }

            if notify_actions.send_email_message("nps_survey", answer.user.email, data, academy=event.academy):
                answer.sent_at = timezone.now()
                answer.save()

    except Exception as e:
        raise AbortTask(str(e))


@task(bind=False, priority=TaskPriority.NOTIFICATION.value)
def send_liveclass_survey(liveclass_id, **_):
    logger.info("Starting liveclass survey")
    live = LiveClass.objects.filter(id=liveclass_id).first()
    if live is None:
        raise RetryTask("LiveClass doesn't found")

    if not live.ended_at:
        raise AbortTask("This class hasn't finished")

    if timezone.now() - live.ended_at > timedelta(days=1):
        raise AbortTask("This live class finished more than one day ago")

    if Answer.objects.filter(live_class__id=live.id).exists():
        raise AbortTask("There is already a survey for this live class")

    try:
        cohort = live.cohort_time_slot.cohort
        academy = cohort.academy

        # Get settings once for all answers
        settings = AcademyFeedbackSettings.objects.filter(academy=academy).first()
        if settings:
            excluded_cohorts = settings.get_excluded_cohort_ids()
            if cohort.id in excluded_cohorts:
                raise AbortTask(f"Cohort {cohort.id} is excluded from live class surveys")

        template_slug = (
            settings.liveclass_survey_template.slug if settings and settings.liveclass_survey_template else None
        )

        history_log = cohort.history_log or {}
        attended_user_ids = []

        for day_log in history_log.values():
            day_creation_datetime = datetime.fromisoformat(day_log.get("updated_at"))
            if day_creation_datetime - live.ended_at < timedelta(days=1):
                attended_user_ids = day_log.get("attendance_ids", [])
                break

        survey = Survey(cohort=cohort, lang=cohort.language.lower(), is_customized=True, template_slug=template_slug)
        survey.sent_at = timezone.now()
        survey.save()
        for user_id in attended_user_ids:
            cu = CohortUser.objects.filter(user_id=user_id, cohort=cohort, role="STUDENT").first()
            if cu is not None:
                teacher = CohortUser.objects.filter(cohort=cohort, role="TEACHER").first()

                # Main answer
                answer = Answer(
                    live_class=live,
                    user=cu.user,
                    status="SENT",
                    survey=survey,
                    lang=cohort.language,
                    academy=academy,
                    cohort=cohort,
                )
                answer = build_question(answer, template_slug)
                answer.save()

                # Additional questions
                questions = ["live_class_mentor", "live_class_mentor_communication", "live_class_mentor_practice"]
                for slug in questions:
                    a = Answer(
                        question_by_slug=slug,
                        live_class=live,
                        user=cu.user,
                        status="SENT",
                        survey=survey,
                        lang=cohort.language,
                        mentor=teacher.user,
                        academy=academy,
                        cohort=cohort,
                    )
                    # Use same template for additional questions
                    a = build_question(a, template_slug)
                    a.save()

                token, _ = Token.get_or_create(answer.user, token_type="temporal", hours_length=48)

                # lazyload api url in test environment
                api_url = API_URL if ENV != "test" else os.getenv("API_URL", "")
                data = {
                    "SUBJECT": answer.title,
                    "MESSAGE": answer.title,
                    "TRACKER_URL": f"{api_url}/v1/feedback/survey/{survey.id}/tracker.png",
                    "BUTTON": strings[survey.lang.lower()]["button_label"],
                    "LINK": f"https://nps.4geeks.com/survey/{survey.id}?token={token.key}",
                }

                if notify_actions.send_email_message("nps_survey", answer.user.email, data, academy=academy):
                    answer.sent_at = timezone.now()
                    answer.save()
        survey.status = "SENT"
        survey.save()

    except LockError:
        raise RetryTask("Could not acquire lock for activity, operation timed out.")

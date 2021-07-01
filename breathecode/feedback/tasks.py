import logging
from celery import shared_task, Task
from django.utils import timezone
from breathecode.notify.actions import send_email_message, send_slack
from .utils import strings
from breathecode.authenticate.actions import create_token
from breathecode.admissions.models import CohortUser
from django.contrib.auth.models import User
from .models import Survey, Answer
from django.utils import timezone

# Get an instance of a logger
logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


def build_question(answer):

    question = {"title": "", "lowest": "", "highest": ""}
    if answer.event is not None:
        question["title"] = strings[answer.lang]["event"]["title"]
        question["lowest"] = strings[answer.lang]["event"]["lowest"]
        question["highest"] = strings[answer.lang]["event"]["highest"]
    elif answer.mentor is not None:
        question["title"] = strings[answer.lang]["mentor"]["title"].format(
            answer.mentor.first_name + " " + answer.mentor.last_name)
        question["lowest"] = strings[answer.lang]["mentor"]["lowest"]
        question["highest"] = strings[answer.lang]["mentor"]["highest"]
    elif answer.cohort is not None:
        question["title"] = strings[answer.lang]["cohort"]["title"].format(
            answer.cohort.syllabus.certificate.name)
        question["lowest"] = strings[answer.lang]["cohort"]["lowest"]
        question["highest"] = strings[answer.lang]["cohort"]["highest"]
    elif answer.academy is not None:
        question["title"] = strings[answer.lang]["academy"]["title"].format(
            answer.academy.name)
        question["lowest"] = strings[answer.lang]["academy"]["lowest"]
        question["highest"] = strings[answer.lang]["academy"]["highest"]

    return question


def generate_user_cohort_survey_answers(user, survey, status='OPENED'):

    cohort_teacher = CohortUser.objects.filter(cohort=survey.cohort,
                                               role="TEACHER")
    if cohort_teacher.count() == 0:
        raise ValidationException(
            "This cohort must have a teacher assigned to be able to survey it",
            400)

    def new_answer(answer):
        question = build_question(answer)
        answer.title = question["title"]
        answer.lowest = question["lowest"]
        answer.highest = question["highest"]
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
        answer = Answer(cohort=survey.cohort,
                        academy=survey.cohort.academy,
                        lang=survey.lang)
        _answers.append(new_answer(answer))

        # ask for each teacher, with a max of 2 teachers
        cont = 0
        for ct in cohort_teacher:
            if cont >= survey.max_teachers_to_ask:
                break
            answer = Answer(mentor=ct.user,
                            cohort=survey.cohort,
                            academy=survey.cohort.academy,
                            lang=survey.lang)
            _answers.append(new_answer(answer))
            cont = cont + 1

        # ask for the first TA
        cohort_assistant = CohortUser.objects.filter(cohort=survey.cohort,
                                                     role="ASSISTANT")
        cont = 0
        for ca in cohort_assistant:
            if cont >= survey.max_assistants_to_ask:
                break
            answer = Answer(mentor=ca.user,
                            cohort=survey.cohort,
                            academy=survey.cohort.academy,
                            lang=survey.lang)
            _answers.append(new_answer(answer))
            cont = cont + 1

        # ask for the whole academy
        answer = Answer(academy=survey.cohort.academy, lang=survey.lang)
        _answers.append(new_answer(answer))

    return _answers


@shared_task(bind=True, base=BaseTaskWithRetry)
def send_cohort_survey(self, user_id, survey_id):
    logger.debug("Starting send_cohort_survey")
    survey = Survey.objects.filter(id=survey_id).first()
    if survey is None:
        logger.error("Survey not found")
        return False

    user = User.objects.filter(id=user_id).first()
    if user is None:
        logger.error("User not found")
        return False

    utc_now = timezone.now()
    if utc_now > survey.created_at + survey.duration:
        logger.error("This survey has already expired")
        return False

    cu = CohortUser.objects.filter(cohort=survey.cohort,
                                   role="STUDENT",
                                   user=user).first()
    if cu is None:
        raise ValidationException(
            "This student does not belong to this cohort", 400)

    answers = generate_user_cohort_survey_answers(user, survey, status='SENT')

    has_slackuser = hasattr(user, 'slackuser')
    if not user.email and not has_slackuser:
        message = f'Author not have email and slack, this survey cannot be send by {str(user.id)}'
        logger.info(message)
        raise Exception(message)

    token = create_token(user, hours_length=48)
    data = {
        "SUBJECT": strings[survey.lang]["survey_subject"],
        "MESSAGE": strings[survey.lang]["survey_message"],
        "SURVEY_ID": survey_id,
        "BUTTON": strings[survey.lang]["button_label"],
        "LINK":
        f"https://nps.breatheco.de/survey/{survey_id}?token={token.key}",
    }

    if user.email:
        send_email_message("nps_survey", user.email, data)
        survey.sent_at = timezone.now()

    if hasattr(user, 'slackuser') and hasattr(survey.cohort.academy,
                                              'slackteam'):
        send_slack("nps_survey",
                   user.slackuser,
                   survey.cohort.academy.slackteam,
                   data=data)

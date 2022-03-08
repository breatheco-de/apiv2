import logging, os
from breathecode.authenticate.models import Token
from breathecode.utils import validation_exception
from breathecode.utils import getLogger
from django.db.models import Avg
from celery import shared_task, Task
from django.utils import timezone
from breathecode.notify.actions import send_email_message, send_slack
from .utils import strings
from breathecode.admissions.models import CohortUser, Cohort
from django.contrib.auth.models import User
from .models import Survey, Answer, Review, ReviewPlatform
from breathecode.mentorship.models import MentorshipSession
from django.utils import timezone

# Get an instance of a logger
# logger = logging.getLogger(__name__)
logger = getLogger(__name__)

ADMIN_URL = os.getenv('ADMIN_URL', '')
SYSTEM_EMAIL = os.getenv('SYSTEM_EMAIL', '')
API_URL = os.getenv('API_URL', '')


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


def build_question(answer):

    question = {'title': '', 'lowest': '', 'highest': ''}
    if answer.mentorship_session is not None:
        question['title'] = strings[answer.lang]['session']['title'].format(
            f'{answer.mentorship_session.mentor.user.first_name} {answer.mentorship_session.mentor.user.last_name}'
        )
        question['lowest'] = strings[answer.lang]['session']['lowest']
        question['highest'] = strings[answer.lang]['session']['highest']
    elif answer.event is not None:
        question['title'] = strings[answer.lang]['event']['title']
        question['lowest'] = strings[answer.lang]['event']['lowest']
        question['highest'] = strings[answer.lang]['event']['highest']
    elif answer.mentor is not None:
        question['title'] = strings[answer.lang]['mentor']['title'].format(answer.mentor.first_name + ' ' +
                                                                           answer.mentor.last_name)
        question['lowest'] = strings[answer.lang]['mentor']['lowest']
        question['highest'] = strings[answer.lang]['mentor']['highest']
    elif answer.cohort is not None and answer.cohort.syllabus_version:
        question['title'] = strings[answer.lang]['cohort']['title'].format(
            answer.cohort.syllabus_version.syllabus.name)
        question['lowest'] = strings[answer.lang]['cohort']['lowest']
        question['highest'] = strings[answer.lang]['cohort']['highest']
    elif answer.academy is not None:
        question['title'] = strings[answer.lang]['academy']['title'].format(answer.academy.name)
        question['lowest'] = strings[answer.lang]['academy']['lowest']
        question['highest'] = strings[answer.lang]['academy']['highest']

    return question


def generate_user_cohort_survey_answers(user, survey, status='OPENED'):

    cohort_teacher = CohortUser.objects.filter(cohort=survey.cohort, role='TEACHER')
    if cohort_teacher.count() == 0:
        raise ValidationException('This cohort must have a teacher assigned to be able to survey it', 400)

    def new_answer(answer):
        question = build_question(answer)
        answer.title = question['title']
        answer.lowest = question['lowest']
        answer.highest = question['highest']
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
        cohort_assistant = CohortUser.objects.filter(cohort=survey.cohort, role='ASSISTANT')
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
    logger.debug('Starting send_cohort_survey')
    survey = Survey.objects.filter(id=survey_id).first()
    if survey is None:
        logger.error('Survey not found')
        return False

    user = User.objects.filter(id=user_id).first()
    if user is None:
        logger.error('User not found')
        return False

    utc_now = timezone.now()
    if utc_now > survey.created_at + survey.duration:
        logger.error('This survey has already expired')
        return False

    cu = CohortUser.objects.filter(cohort=survey.cohort, role='STUDENT', user=user).first()
    if cu is None:
        raise ValidationException('This student does not belong to this cohort', 400)

    answers = generate_user_cohort_survey_answers(user, survey, status='SENT')

    has_slackuser = hasattr(user, 'slackuser')
    if not user.email and not has_slackuser:
        message = f'Author not have email and slack, this survey cannot be send by {str(user.id)}'
        logger.info(message)
        raise Exception(message)

    token, created = Token.get_or_create(user, token_type='temporal', hours_length=48)
    data = {
        'SUBJECT': strings[survey.lang]['survey_subject'],
        'MESSAGE': strings[survey.lang]['survey_message'],
        'TRACKER_URL': f'{API_URL}/v1/feedback/survey/{survey_id}/tracker.png',
        'BUTTON': strings[survey.lang]['button_label'],
        'LINK': f'https://nps.breatheco.de/survey/{survey_id}?token={token.key}',
    }

    if user.email:
        send_email_message('nps_survey', user.email, data)

    if hasattr(user, 'slackuser') and hasattr(survey.cohort.academy, 'slackteam'):
        send_slack('nps_survey', user.slackuser, survey.cohort.academy.slackteam, data=data)


@shared_task(bind=True, base=BaseTaskWithRetry)
def process_student_graduation(self, cohort_id, user_id):
    from .actions import create_user_graduation_reviews

    logger.debug('Starting process_student_graduation')

    cohort = Cohort.objects.filter(id=cohort_id).first()
    if cohort is None:
        raise ValidationException(f'Invalid cohort id: {cohort_id}')
    user = User.objects.filter(id=user_id).first()
    if user is None:
        raise ValidationException(f'Invalid user id: {user_id}')

    create_user_graduation_reviews(user, cohort)

    return True


@shared_task(bind=True, base=BaseTaskWithRetry)
def process_answer_received(self, answer_id):
    """
    This task will be called every time a single NPS answer is received
    the task will reivew the score, if we got less than 7 it will notify
    the school.
    """

    from breathecode.notify.actions import send_email_message

    logger.debug('Starting notify_bad_nps_score')
    answer = Answer.objects.filter(id=answer_id).first()
    if answer is None:
        logger.error('Answer not found')
        return

    if answer.survey is None:
        logger.error('No survey connected to answer.')
        return

    survey_score = Answer.objects.filter(survey=answer.survey).aggregate(Avg('score'))
    answer.survey.avg_score = survey_score['score__avg']

    total_responses = Answer.objects.filter(survey=answer.survey).count()
    answered_responses = Answer.objects.filter(survey=answer.survey, status='ANSWERED').count()
    response_rate = (answered_responses / total_responses) * 100
    answer.survey.response_rate = response_rate
    answer.survey.save()

    if answer.user and answer.academy and answer.score is not None and answer.score < 8:

        list_of_emails = []

        if SYSTEM_EMAIL is not None:
            list_of_emails.append(SYSTEM_EMAIL)
        else:
            logger.exception('No system email found.', slug='system-email-notfound')
            return

        if answer.academy.feedback_email is not None:
            list_of_emails.append(answer.academy.feedback_email)

        else:
            logger.exception('No academy feedback email found.', slug='academy-feedback-email-not-found')
            return

        # TODO: instead of sending, use notifications system to be built on the breathecode.admin app.
        send_email_message('negative_answer',
                           list_of_emails,
                           data={
                               'SUBJECT': f'A student answered with a bad NPS score at {answer.academy.name}',
                               'FULL_NAME': answer.user.first_name + ' ' + answer.user.last_name,
                               'QUESTION': answer.title,
                               'SCORE': answer.score,
                               'COMMENTS': answer.comment,
                               'ACADEMY': answer.academy.name,
                               'LINK':
                               f'{ADMIN_URL}/feedback/surveys/{answer.academy.slug}/{answer.survey.id}'
                           })

    return True


@shared_task(bind=True, base=BaseTaskWithRetry)
def send_mentorship_session_survey(self, session_id):
    logger.debug('Starting send_mentorship_session_survey')
    session = MentorshipSession.objects.filter(id=session_id).first()
    if session is None:
        logger.error('Mentoring session not found')
        return False

    answer = Answer.objects.filter(mentorship_session__id=session.id).first()
    if answer is None:
        answer = Answer(mentorship_session=session,
                        academy=session.mentor.service.academy,
                        lang=session.mentor.service.language)
        question = build_question(answer)
        answer.title = question['title']
        answer.lowest = question['lowest']
        answer.highest = question['highest']
        answer.user = session.mentee
        answer.status = 'SENT'
        answer.save()
    elif answer.status == 'ANSWERED':
        return False

    has_slackuser = hasattr(session.mentee, 'slackuser')
    if not session.mentee.email:
        message = f'Author not have email, this survey cannot be send by {str(session.mentee.id)}'
        logger.info(message)
        raise Exception(message)

    token, created = Token.get_or_create(session.mentee, token_type='temporal', hours_length=48)
    data = {
        'SUBJECT': strings[answer.lang]['survey_subject'],
        'MESSAGE': answer.title,
        'TRACKER_URL': f'{API_URL}/v1/feedback/answer/{answer.id}/tracker.png',
        'BUTTON': strings[answer.lang]['button_label'],
        'LINK': f'https://nps.breatheco.de/{answer.id}?token={token.key}',
    }

    if session.mentee.email:
        if send_email_message('nps_survey', session.mentee.email, data):
            answer.sent_at = timezone.now()
            answer.save()

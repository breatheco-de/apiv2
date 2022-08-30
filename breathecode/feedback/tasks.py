from datetime import timedelta
import os
from breathecode.authenticate.models import Token
from breathecode.utils import ValidationException
from breathecode.utils import getLogger
from django.db.models import Avg
from celery import shared_task, Task
from django.utils import timezone
from breathecode.notify import actions as notify_actions
from .utils import strings
from breathecode.utils import getLogger
from breathecode.admissions.models import CohortUser, Cohort
from django.contrib.auth.models import User
from .models import Survey, Answer
from breathecode.mentorship.models import MentorshipSession
from django.utils import timezone
from . import actions

# Get an instance of a logger
logger = getLogger(__name__)

ADMIN_URL = os.getenv('ADMIN_URL', '')
API_URL = os.getenv('API_URL', '')
ENV = os.getenv('ENV', '')


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


def build_question(answer):
    lang = answer.lang.lower()
    question = {'title': '', 'lowest': '', 'highest': ''}
    if answer.mentorship_session is not None:
        question['title'] = strings[lang]['session']['title'].format(
            f'{answer.mentorship_session.mentor.user.first_name} {answer.mentorship_session.mentor.user.last_name}'
        )
        question['lowest'] = strings[lang]['session']['lowest']
        question['highest'] = strings[lang]['session']['highest']
    elif answer.event is not None:
        question['title'] = strings[lang]['event']['title']
        question['lowest'] = strings[lang]['event']['lowest']
        question['highest'] = strings[lang]['event']['highest']
    elif answer.mentor is not None:
        question['title'] = strings[lang]['mentor']['title'].format(answer.mentor.first_name + ' ' +
                                                                    answer.mentor.last_name)
        question['lowest'] = strings[lang]['mentor']['lowest']
        question['highest'] = strings[lang]['mentor']['highest']
    elif answer.cohort is not None:
        title = answer.cohort.syllabus_version.syllabus.name if answer.cohort.syllabus_version \
            and answer.cohort.syllabus_version.syllabus.name else answer.cohort.name

        question['title'] = strings[lang]['cohort']['title'].format(title)
        question['lowest'] = strings[lang]['cohort']['lowest']
        question['highest'] = strings[lang]['cohort']['highest']
    elif answer.academy is not None:
        question['title'] = strings[lang]['academy']['title'].format(answer.academy.name)
        question['lowest'] = strings[lang]['academy']['lowest']
        question['highest'] = strings[lang]['academy']['highest']

    return question


def get_system_email():
    system_email = os.getenv('SYSTEM_EMAIL')
    return system_email


def get_admin_url():
    admin_url = os.getenv('ADMIN_URL')
    return admin_url


def generate_user_cohort_survey_answers(user, survey, status='OPENED'):

    if not CohortUser.objects.filter(
            cohort=survey.cohort, role='STUDENT', user=user, educational_status__in=['ACTIVE', 'GRADUATED'
                                                                                     ]).exists():
        raise ValidationException('This student does not belong to this cohort', 400)

    cohort_teacher = CohortUser.objects.filter(cohort=survey.cohort,
                                               role='TEACHER',
                                               educational_status__in=['ACTIVE', 'GRADUATED'])
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
        cohort_assistant = CohortUser.objects.filter(cohort=survey.cohort,
                                                     role='ASSISTANT',
                                                     educational_status__in=['ACTIVE', 'GRADUATED'])
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


def api_url():
    return os.getenv('API_URL', '')


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

    cu = CohortUser.objects.filter(cohort=survey.cohort,
                                   role='STUDENT',
                                   user=user,
                                   educational_status__in=['ACTIVE', 'GRADUATED']).first()
    if cu is None:
        logger.error('This student does not belong to this cohort')
        return False

    #TODO:test function below
    answers = generate_user_cohort_survey_answers(user, survey, status='SENT')

    has_slackuser = hasattr(user, 'slackuser')
    if not user.email and not has_slackuser:
        message = f'Author not have email and slack, this survey cannot be send by {str(user.id)}'
        logger.debug(message)
        raise Exception(message)

    token, created = Token.get_or_create(user, token_type='temporal', hours_length=48)
    data = {
        'SUBJECT': strings[survey.lang]['survey_subject'],
        'MESSAGE': strings[survey.lang]['survey_message'],
        'TRACKER_URL': f'{api_url()}/v1/feedback/survey/{survey_id}/tracker.png',
        'BUTTON': strings[survey.lang]['button_label'],
        'LINK': f'https://nps.breatheco.de/survey/{survey_id}?token={token.key}',
    }

    if user.email:

        notify_actions.send_email_message('nps_survey', user.email, data)

    if hasattr(user, 'slackuser') and hasattr(survey.cohort.academy, 'slackteam'):
        notify_actions.send_slack('nps_survey', user.slackuser, survey.cohort.academy.slackteam, data=data)


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
def recalculate_survey_scores(self, survey_id):
    logger.debug('Starting recalculate_survey_score')

    survey = Survey.objects.filter(id=survey_id).first()
    if survey is None:
        logger.error('Survey not found')
        return

    survey.response_rate = actions.calculate_survey_response_rate(survey.id)
    survey.scores = actions.calculate_survey_scores(survey.id)
    survey.save()


@shared_task(bind=True, base=BaseTaskWithRetry)
def process_answer_received(self, answer_id):
    """
    This task will be called every time a single NPS answer is received
    the task will review the score, if we got less than 7 it will notify
    the school.
    """

    logger.debug('Starting notify_bad_nps_score')
    answer = Answer.objects.filter(id=answer_id).first()
    if answer is None:
        logger.error('Answer not found')
        return

    if answer.survey is None:
        logger.error('No survey connected to answer.')
        return

    answer.survey.response_rate = actions.calculate_survey_response_rate(answer.survey.id)
    answer.survey.scores = actions.calculate_survey_scores(answer.survey.id)
    answer.survey.save()

    if answer.user and answer.academy and answer.score is not None and answer.score < 8:
        system_email = get_system_email()
        admin_url = get_admin_url()
        list_of_emails = []

        if system_email is not None:
            list_of_emails.append(system_email)
        else:
            logger.error('No system email found.', slug='system-email-not-found')

        if answer.academy.feedback_email is not None:
            list_of_emails.append(answer.academy.feedback_email)

        else:
            logger.error('No academy feedback email found.', slug='academy-feedback-email-not-found')

        # TODO: instead of sending, use notifications system to be built on the breathecode.admin app.
        if list_of_emails:
            notify_actions.send_email_message(
                'negative_answer',
                list_of_emails,
                data={
                    'SUBJECT': f'A student answered with a bad NPS score at {answer.academy.name}',
                    'FULL_NAME': answer.user.first_name + ' ' + answer.user.last_name,
                    'QUESTION': answer.title,
                    'SCORE': answer.score,
                    'COMMENTS': answer.comment,
                    'ACADEMY': answer.academy.name,
                    'LINK': f'{admin_url}/feedback/surveys/{answer.academy.slug}/{answer.survey.id}'
                })

    return True


@shared_task(bind=True, base=BaseTaskWithRetry)
def send_mentorship_session_survey(self, session_id):
    logger.debug('Starting send_mentorship_session_survey')
    session = MentorshipSession.objects.filter(id=session_id).first()
    if session is None:
        logger.error('Mentoring session not found', slug='without-mentorship-session')
        return False

    if session.mentee is None:
        logger.error('The current session not have a mentee', slug='mentorship-session-without-mentee')
        return False

    if not session.started_at or not session.ended_at:
        logger.error('Mentorship session not finished',
                     slug='mentorship-session-without-started-at-or-ended-at')
        return False

    if session.ended_at - session.started_at <= timedelta(minutes=5):
        logger.error('Mentorship session duration less or equal than five minutes',
                     slug='mentorship-session-duration-less-or-equal-than-five-minutes')
        return False

    if not session.service:
        logger.error('Mentorship session not have a service associated with it',
                     slug='mentorship-session-not-have-a-service-associated-with-it')
        return False

    answer = Answer.objects.filter(mentorship_session__id=session.id).first()
    if answer is None:
        answer = Answer(mentorship_session=session,
                        academy=session.mentor.academy,
                        lang=session.service.language)
        question = build_question(answer)
        answer.title = question['title']
        answer.lowest = question['lowest']
        answer.highest = question['highest']
        answer.user = session.mentee
        answer.status = 'SENT'
        answer.save()
    elif answer.status == 'ANSWERED':
        logger.debug(f'This survey about MentorshipSession {session.id} was answered',
                     slug='answer-with-status-answered')
        return False

    has_slackuser = hasattr(session.mentee, 'slackuser')
    if not session.mentee.email:
        message = f'Author not have email, this survey cannot be send by {session.mentee.id}'
        logger.debug(message, slug='mentee-without-email')
        return False

    token, created = Token.get_or_create(session.mentee, token_type='temporal', hours_length=48)

    # lazyload api url in test environment
    api_url = API_URL if ENV != 'test' else os.getenv('API_URL', '')
    data = {
        'SUBJECT': strings[answer.lang.lower()]['survey_subject'],
        'MESSAGE': answer.title,
        'TRACKER_URL': f'{api_url}/v1/feedback/answer/{answer.id}/tracker.png',
        'BUTTON': strings[answer.lang.lower()]['button_label'],
        'LINK': f'https://nps.breatheco.de/{answer.id}?token={token.key}',
    }

    if session.mentee.email:
        if notify_actions.send_email_message('nps_survey', session.mentee.email, data):
            answer.sent_at = timezone.now()
            answer.save()

import logging, os
from breathecode.authenticate.models import Token
from breathecode.utils import ValidationException
from django.db.models import Avg
from celery import shared_task, Task
from django.utils import timezone
from breathecode.notify.actions import send_email_message, send_slack
from .utils import strings
from breathecode.admissions.models import CohortUser, Cohort
from django.contrib.auth.models import User
from .models import Survey, Answer, Review, ReviewPlatform
from django.utils import timezone

# Get an instance of a logger
logger = logging.getLogger(__name__)

ADMIN_URL = os.getenv('ADMIN_URL', '')
SYSTEM_EMAIL = os.getenv('SYSTEM_EMAIL', '')


def get_student_answer_avg(user_id, cohort_id=None, academy_id=None):

    answers = Answer.objects.filter(user__id=user_id, status='ANSWERED', score__isnull=False)

    # optionally filter by cohort
    if cohort_id is not None:
        answers = answers.filter(cohort__id=cohort_id)

    # optionally filter by academy
    if academy_id is not None:
        answers = answers.filter(academy__id=academy_id)

    query = answers.aggregate(average=Avg('score'))

    return query['average']


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


def build_question(answer):

    question = {'title': '', 'lowest': '', 'highest': ''}
    if answer.event is not None:
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

    token, created = Token.get_or_create(user, hours_length=48)
    data = {
        'SUBJECT': strings[survey.lang]['survey_subject'],
        'MESSAGE': strings[survey.lang]['survey_message'],
        'SURVEY_ID': survey_id,
        'BUTTON': strings[survey.lang]['button_label'],
        'LINK': f'https://nps.breatheco.de/survey/{survey_id}?token={token.key}',
    }

    if user.email:
        send_email_message('nps_survey', user.email, data)
        survey.sent_at = timezone.now()

    if hasattr(user, 'slackuser') and hasattr(survey.cohort.academy, 'slackteam'):
        send_slack('nps_survey', user.slackuser, survey.cohort.academy.slackteam, data=data)


@shared_task(bind=True, base=BaseTaskWithRetry)
def process_student_graduation(self, cohort_id, user_id):
    logger.debug('Starting process_student_graduation')

    cohort = Cohort.objects.filter(id=cohort_id).first()
    if cohort is None:
        raise ValidationException(f'Invalid cohort id: {cohort_id}')
    user = User.objects.filter(id=user_id).first()
    if user is None:
        raise ValidationException(f'Invalid user id: {user_id}')

    # If the user gave us a rating >7 we should create reviews for each review platform with status "pending"
    average = get_student_answer_avg(user_id, cohort_id)
    if average is None or average >= 8:
        total_reviews = Review.objects.filter(
            cohort=cohort,
            author=user,
        ).count()
        if total_reviews > 0:
            logger.debug(
                f'No new reviews will be requested, student already has pending requests for this cohort')
            return False

        platforms = ReviewPlatform.objects.all()
        logger.debug(
            f'{platforms.count()} will be requested for student {user.id}, avg NPS score of {average}')
        for plat in platforms:
            review = Review(cohort=cohort, author=user, platform=plat)
            review.save()

        return True

    logger.debug(f'No reviews requested for student {user.id} because average NPS score is {average}')
    return False


@shared_task(bind=True, base=BaseTaskWithRetry)
def process_answer_received(self, answer_id):
    """
    This task will be called every time a single NPS answer is received
    the task will reivew the score, if we got less than 7 it will notify
    the school.
    """
    logger.debug('Starting notify_bad_nps_score')
    answer = Answer.objects.filter(id=answer_id).first()
    if answer is None:
        raise ValidationException('Answer not found')

    if answer.survey is not None:
        survey_score = Answer.objects.filter(survey=answer.survey).aggregate(Avg('score'))
        answer.survey.avg_score = survey_score['score__avg']
        answer.survey.save()

    if answer.score < 8:
        # TODO: instead of sending, use notifications system to be built on the breathecode.admin app.
        send_email_message('negative_answer', [SYSTEM_EMAIL, answer.academy.feedback_email],
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

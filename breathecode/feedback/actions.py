from breathecode.notify.actions import send_email_message, send_slack
import logging, random
from django.utils import timezone
from django.db.models import Avg
from breathecode.utils import ValidationException
from breathecode.authenticate.models import Token
from .models import Answer, Survey, Review, ReviewPlatform
from .utils import strings
from breathecode.admissions.models import CohortUser
from .tasks import send_cohort_survey, build_question

logger = logging.getLogger(__name__)


def send_survey_group(survey=None, cohort=None):

    if survey is None and cohort is None:
        raise ValidationException('Missing survey or cohort')

    if survey is None:
        survey = Survey(cohort=cohort, lang=cohort.language)

    try:

        if cohort is not None:
            if survey.cohort.id != cohort.id:
                raise ValidationException('The survey does not match the cohort id')

        if cohort is None:
            cohort = survey.cohort

        cohort_teacher = CohortUser.objects.filter(cohort=survey.cohort, role='TEACHER')
        if cohort_teacher.count() == 0:
            raise ValidationException('This cohort must have a teacher assigned to be able to survey it', 400)

        ucs = CohortUser.objects.filter(cohort=cohort, role='STUDENT').filter()
        result = {'success': [], 'error': []}
        for uc in ucs:
            if uc.educational_status in ['ACTIVE', 'GRADUATED']:
                send_cohort_survey.delay(uc.user.id, survey.id)
                logger.debug(f'Survey scheduled to send for {uc.user.email}')
                result['success'].append(f'Survey scheduled to send for {uc.user.email}')
            else:
                logger.debug(
                    f"Survey NOT sent to {uc.user.email} because it's not an active or graduated student")
                result['error'].append(
                    f"Survey NOT sent to {uc.user.email} because it's not an active or graduated student")
        survey.sent_at = timezone.now()
        survey.save()

    except Exception as e:
        survey.status = 'FATAL'
        result['error'].append(f'Error sending survey to group: ' + str(e))
        survey.status_json = json.dumps(result)
        survey.save()
        raise e

    return result


def send_question(user, cohort=None):
    answer = Answer(user=user)
    if cohort is not None:
        answer.cohort = cohort
    else:
        cohorts = CohortUser.objects.filter(user__id=user.id).order_by('-cohort__kickoff_date')
        _count = cohorts.count()
        if _count == 1:
            _cohort = cohorts.first().cohort
            answer.cohort = _cohort

    if answer.cohort is None:
        raise ValidationException(
            'Impossible to determine the student cohort, maybe it has more than one, or cero.',
            slug='without-cohort-or-cannot-determine-cohort')
    else:
        answer.lang = answer.cohort.language
        answer.save()

    has_slackuser = hasattr(user, 'slackuser')

    if not user.email and not has_slackuser:
        raise ValidationException(
            f'User not have email and slack, this survey cannot be send: {str(user.id)}',
            slug='without-email-or-slack-user')

    if not answer.cohort.syllabus_version:
        raise ValidationException('Cohort not have one SyllabusVersion',
                                  slug='cohort-without-syllabus-version')

    if not answer.cohort.specialty_mode:
        raise ValidationException('Cohort not have one SpecialtyMode', slug='cohort-without-specialty-mode')

    question_was_sent_previously = Answer.objects.filter(cohort=answer.cohort, user=user,
                                                         status='SENT').count()

    question = build_question(answer)

    if question_was_sent_previously:
        answer = Answer.objects.filter(cohort=answer.cohort, user=user, status='SENT').first()
        Token.objects.filter(id=answer.token_id).delete()

    else:
        answer.title = question['title']
        answer.lowest = question['lowest']
        answer.highest = question['highest']
        answer.lang = answer.cohort.language
        answer.save()

    token, created = Token.get_or_create(user, token_type='temporal', hours_length=48)

    token_id = Token.objects.filter(key=token).values_list('id', flat=True).first()
    answer.token_id = token_id
    answer.save()

    data = {
        'QUESTION': question['title'],
        'HIGHEST': answer.highest,
        'LOWEST': answer.lowest,
        'SUBJECT': question['title'],
        'ANSWER_ID': answer.id,
        'BUTTON': strings[answer.cohort.language]['button_label'],
        'LINK': f'https://nps.breatheco.de/{answer.id}?token={token.key}',
    }

    if user.email:
        send_email_message('nps', user.email, data)

    if hasattr(user, 'slackuser') and hasattr(answer.cohort.academy, 'slackteam'):
        send_slack('nps', user.slackuser, answer.cohort.academy.slackteam, data=data)

    # keep track of sent survays until they get answered
    if not question_was_sent_previously:
        logger.info(f'Survey was sent for user: {str(user.id)}')
        answer.status = 'SENT'
        answer.save()
        return True

    else:
        logger.info(f'Survey was resent for user: {str(user.id)}')
        return True


def answer_survey(user, data):
    answer = Answer.objects.create(**{**data, 'user': user})


def get_student_answer_avg(user_id, cohort_id=None, academy_id=None):

    answers = Answer.objects.filter(user__id=user_id, status='ANSWERED', score__isnull=False)

    # optionally filter by cohort
    if cohort_id is not None:
        answers = answers.filter(cohort__id=cohort_id)

    # optionally filter by academy
    if academy_id is not None:
        answers = answers.filter(academy__id=academy_id)

    query = answers.aggregate(average=Avg('score'))

    if query['average'] is not None:
        return round(query['average'], 2)

    return query['average']


def create_user_graduation_reviews(user, cohort):

    # If the user gave us a rating >=8 we should create reviews for each review platform with status "pending"
    average = get_student_answer_avg(user.id, cohort.id)
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
            review = Review(cohort=cohort, author=user, platform=plat, nps_previous_rating=average)
            review.save()

        return True

    logger.debug(f'No reviews requested for student {user.id} because average NPS score is {average}')
    return False

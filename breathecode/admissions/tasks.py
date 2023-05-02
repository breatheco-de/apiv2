import logging, os
from celery import shared_task, Task

from breathecode.authenticate.models import ProfileAcademy, Role
from breathecode.services import Emit
from .models import Cohort, CohortUser, SyllabusVersion
from .actions import test_syllabus
from django.utils import timezone
from django.contrib.auth.models import User
from breathecode.notify import actions as notify_actions
from breathecode.admissions.serializers import GetCohortUserSerializer

API_URL = os.getenv('API_URL', '')

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task
def async_test_syllabus(syllabus_slug, syllabus_version) -> None:
    logger.debug(f'Process async_test_syllabus')

    syl_version = SyllabusVersion.objects.filter(syllabus__slug=syllabus_slug,
                                                 version=syllabus_version).first()
    if syl_version is None:
        logger.error(f'Syllabus {syllabus_slug} v{syllabus_version} not found')

    syl_version.integrity_status = 'PENDING'
    syl_version.integrity_check_at = timezone.now()
    try:
        report = test_syllabus(syl_version.json)
        syl_version.integrity_report = report.serialize()
        if report.http_status() == 200:
            syl_version.integrity_status = 'OK'
        else:
            syl_version.integrity_status = 'ERROR'

    except Exception as e:
        syl_version.integrity_report = {'errors': [str(e)], 'warnings': []}
        syl_version.integrity_status = 'ERROR'
    syl_version.save()

    #FIXME: this doesn't work
    if syl_version.status == 'ERROR':
        notify_actions.send_email_message(
            'diagnostic', user.email, {
                'SUBJECT': f'Critical error error found on syllabus {syllabus_slug} v{version}',
                'details': [f'- {item}\n' for error in syl_version.integrity_report.errors]
            })


@shared_task
def build_cohort_user(cohort_id: int, user_id: int, role: str = 'STUDENT') -> None:
    logger.info(f'Starting build_cohort_user for cohort {cohort_id} and user {user_id}')

    bad_stages = ['DELETED', 'ENDED', 'FINAL_PROJECT', 'STARTED']

    if not (cohort := Cohort.objects.filter(id=cohort_id).exclude(stage__in=bad_stages).first()):
        logger.error(f'Cohort with id {cohort_id} not found')
        return

    if not (user := User.objects.filter(id=user_id, is_active=True).first()):
        logger.error(f'User with id {user_id} not found')
        return

    cohort_user, created = CohortUser.objects.get_or_create(cohort=cohort,
                                                            user=user,
                                                            role=role,
                                                            defaults={
                                                                'finantial_status': 'UP_TO_DATE',
                                                                'educational_status': 'ACTIVE',
                                                            })

    if created:
        logger.info('User added to cohort')

    if role == 'TEACHER':
        role = 'teacher'

    elif role == 'ASSISTANT':
        role = 'assistant'

    elif role == 'REVIEWER':
        role = 'homework_reviewer'

    else:
        role = 'student'

    role = Role.objects.filter(slug=role).first()

    profile, created = ProfileAcademy.objects.get_or_create(academy=cohort.academy,
                                                            user=user,
                                                            role=role,
                                                            defaults={
                                                                'email': user.email,
                                                                'first_name': user.first_name,
                                                                'last_name': user.last_name,
                                                                'last_name': user.last_name,
                                                                'status': 'ACTIVE',
                                                            })

    if profile.status != 'ACTIVE':
        profile.status = 'ACTIVE'
        profile.save()
        logger.info('ProfileAcademy mark as active')

    if created:
        logger.info('ProfileAcademy added')

    serializer = GetCohortUserSerializer(cohort_user, many=False)

    emit = Emit()
    emit.websocket.send('admissions.CohortUser', cohort_user.id, response=serializer.data)

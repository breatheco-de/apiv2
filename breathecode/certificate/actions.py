"""
Certificate actions
"""
import hashlib
import requests, os, logging
from django.utils import timezone
from urllib.parse import urlencode
from breathecode.admissions.models import CohortUser, FULLY_PAID, UP_TO_DATE
from breathecode.assignments.models import Task
from breathecode.utils import ValidationException, APIException
from .models import ERROR, PERSISTED, UserSpecialty, LayoutDesign
from ..services.google_cloud import Storage

logger = logging.getLogger(__name__)
ENVIRONMENT = os.getenv('ENV', None)
BUCKET_NAME = "certificates-breathecode"

strings = {
    "es": {
        "Main Instructor": "Instructor Principal",
    },
    "en": {
        "Main Instructor": "Main Instructor",
    }
}


def generate_certificate(user, cohort=None):
    query = {'user__id': user.id}

    if cohort:
        query['cohort__id'] = cohort.id

    cohort_user = CohortUser.objects.filter(**query).first()

    if not cohort_user:
        message = (
            "Impossible to obtain the student cohort, maybe it's none assigned"
        )
        logger.error(message)
        raise ValidationException(message)

    if not cohort:
        cohort = cohort_user.cohort

    if cohort.syllabus is None:
        message = f"The cohort has no syllabus assigned, please set a syllabus for cohort: {cohort.name}"
        logger.error(message)
        raise ValidationException(message)

    if cohort.syllabus.certificate is None:
        message = ('The cohort has no certificate assigned, please set a '
                   f'certificate for cohort: {cohort.name}')
        logger.error(message)
        raise ValidationException(message)

    if (not hasattr(cohort.syllabus.certificate, 'specialty')
            or not cohort.syllabus.certificate.specialty):
        message = (
            'Specialty has no certificate assigned, please set a '
            f'certificate on the Specialty model: {cohort.syllabus.certificate.name}'
        )
        logger.error(message)
        raise ValidationException(message)

    uspe = UserSpecialty.objects.filter(user=user, cohort=cohort).first()

    if (uspe is not None and uspe.status == 'PERSISTED' and uspe.preview_url):
        message = "This user already has a certificate created"
        logger.error(message)
        raise ValidationException(message)

    if uspe is None:
        utc_now = timezone.now()
        uspe = UserSpecialty(
            user=user,
            cohort=cohort,
            token=hashlib.sha1(
                (str(user.id) + str(utc_now)).encode("UTF-8")).hexdigest(),
            specialty=cohort.syllabus.certificate.specialty,
            signed_by_role=strings[cohort.language]["Main Instructor"],
        )
        if cohort.syllabus.certificate.specialty.expiration_day_delta is not None:
            uspe.expires_at = utc_now + timezone.timedelta(
                days=cohort.syllabus.certificate.specialty.expiration_day_delta
            )

    layout = LayoutDesign.objects.filter(slug='default').first()
    if layout is None:
        message = "Missing a default layout"
        logger.error(message)
        raise ValidationException(message)

    uspe.layout = layout

    # validate for teacher
    main_teacher = CohortUser.objects.filter(cohort__id=cohort.id,
                                             role='TEACHER').first()
    if main_teacher is None or main_teacher.user is None:
        message = "This cohort does not have a main teacher, please assign it first"
        logger.error(message)
        raise ValidationException(message)

    main_teacher = main_teacher.user
    uspe.signed_by = main_teacher.first_name + " " + main_teacher.last_name

    try:
        uspe.academy = cohort.academy
        tasks = Task.objects.filter(user__id=user.id, task_type='PROJECT')
        tasks_count_pending = sum(task.task_status == 'PENDING'
                                  for task in tasks)

        if tasks_count_pending:
            raise ValidationException(f'The student has {tasks_count_pending} '
                                      'pending tasks')

        if not (cohort_user.finantial_status == FULLY_PAID
                or cohort_user.finantial_status == UP_TO_DATE):
            raise ValidationException('The student must have finantial status '
                                      'FULLY_PAID or UP_TO_DATE')

        if cohort_user.educational_status != 'GRADUATED':
            raise ValidationException('The student must have educational '
                                      'status GRADUATED')

        if cohort.current_day != cohort.syllabus.certificate.duration_in_days:
            raise ValidationException(
                'Cohort current day should be '
                f'{cohort.syllabus.certificate.duration_in_days}')

        if cohort.stage != 'ENDED':
            message = f"The student cohort stage has to be 'ENDED' before you can issue any certificates"
            logger.error(message)
            raise ValidationException(message)

        uspe.status = PERSISTED
        uspe.status_text = "Certificate successfully queued for PDF generation"
        uspe.save()

    except Exception as e:
        message = str(e)
        uspe.status = ERROR
        uspe.status_text = message
        logger.error(message)
        uspe.save()

    return uspe


def certificate_screenshot(certificate_id: int):

    certificate = UserSpecialty.objects.get(id=certificate_id)
    if certificate.preview_url is None or certificate.preview_url == "":
        file_name = f'{certificate.token}'

        storage = Storage()
        file = storage.file(BUCKET_NAME, file_name)

        # if the file does not exist
        if file.blob is None:
            query_string = urlencode({
                'key':
                os.environ.get('SCREENSHOT_MACHINE_KEY'),
                'url':
                f'https://certificate.breatheco.de/preview/{certificate.token}',
                'device':
                'desktop',
                'cacheLimit':
                '0',
                'dimension':
                '1024x707',
            })
            r = requests.get(
                f'https://api.screenshotmachine.com?{query_string}',
                stream=True)
            if r.status_code == 200:
                file.upload(r.content, public=True)
            else:
                print("Invalid reponse code: ", r.status_code)

        # after created, lets save the URL
        if file.blob is not None:
            certificate.preview_url = file.url()
            certificate.save()


def remove_certificate_screenshot(certificate_id):
    certificate = UserSpecialty.objects.get(id=certificate_id)
    if certificate.preview_url is None or certificate.preview_url == "":
        return False

    file_name = certificate.token
    storage = Storage()
    file = storage.file(BUCKET_NAME, file_name)
    file.delete()

    certificate.preview_url = ""
    certificate.save()

    return True

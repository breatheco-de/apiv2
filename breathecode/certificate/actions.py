"""
Certificate actions
"""
import requests, os, logging
from urllib.parse import urlencode
from breathecode.admissions.models import CohortUser, FULLY_PAID, UP_TO_DATE
from breathecode.assignments.models import Task
from breathecode.utils import ValidationException
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

def report_certificate_error(message: str, user, cohort, layout=None):
    try:
        uspe = UserSpecialty.objects.filter(user=user, cohort=cohort).first()
        if uspe is None:
            uspe = UserSpecialty(
                user = user,
                cohort = cohort,
            )

        uspe.specialty = cohort.certificate.specialty
        uspe.academy = cohort.academy
        uspe.status_text = message
        uspe.status = ERROR
        uspe.preview_url = None

        if layout:
            uspe.layout = layout
        # uspe.is_cleaned = True

        uspe.save()
    except Exception as e:
        logger.error('User Specialty should not be saved')
        logger.error(str(e))

    logger.error(message)
    return ValidationException(message)

def generate_certificate(user, cohort=None):

    cohort_user = CohortUser.objects.filter(user__id=user.id).first()
    tasks = Task.objects.filter(user__id=user.id, task_type='PROJECT')
    tasks_count_pending = sum(task.task_status == 'PENDING' for task in tasks)

    if not cohort and cohort_user:
        cohort = cohort_user.cohort

    if cohort is None:
        message = "Imposible to obtain the student cohort, maybe it has more than one or none assigned"
        raise report_certificate_error(message, user, cohort)

    if tasks_count_pending:
        message = f'The student have {tasks_count_pending} pending tasks'
        raise report_certificate_error(message, user, cohort)

    if not (cohort_user.finantial_status == FULLY_PAID or cohort_user.finantial_status ==
        UP_TO_DATE):
        message = f'The student must have finantial status FULLY_PAID or UP_TO_DATE'
        raise report_certificate_error(message, user, cohort)

    if cohort.certificate is None:
        message = f"The cohort has no certificate assigned, please set a certificate for cohort: {cohort.name}"
        raise report_certificate_error(message, user, cohort)

    if cohort.certificate.specialty is None:
        message = f"Specialty has no certificate assigned, please set a certificate on the Specialty model: {cohort.certificate.name}"
        raise report_certificate_error(message, user, cohort)

    if cohort.current_day != cohort.certificate.duration_in_days:
        message = "cohort.current_day is not equal to certificate.duration_in_days"
        raise report_certificate_error(message, user, cohort)

    layout = LayoutDesign.objects.filter(slug='default').first()
    if layout is None:
        message = "Missing a default layout"
        raise report_certificate_error(message, user, cohort)

    main_teacher = CohortUser.objects.filter(cohort__id=cohort.id, role='TEACHER').first()
    if main_teacher is None or main_teacher.user is None:
        message = "This cohort does not have a main teacher, please assign it first"
        raise report_certificate_error(message, user, cohort, layout)
    else:
        main_teacher = main_teacher.user

    uspe = UserSpecialty.objects.filter(user=user, cohort=cohort).first()
    if uspe is None:
        uspe = UserSpecialty(
            user = user,
            cohort = cohort,
        )

    uspe.specialty = cohort.certificate.specialty
    uspe.academy = cohort.academy
    uspe.layout = layout
    uspe.signed_by = main_teacher.first_name + " " + main_teacher.last_name
    uspe.signed_by_role = strings[cohort.language]["Main Instructor"]
    uspe.status = PERSISTED
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
                'key': os.environ.get('SCREENSHOT_MACHINE_KEY'),
                'url': f'https://certificate.breatheco.de/preview/{certificate.token}',
                'device': 'desktop',
                'cacheLimit': '0',
                'dimension': '1024x707',
            })
            r = requests.get(f'https://api.screenshotmachine.com?{query_string}', stream=True)
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

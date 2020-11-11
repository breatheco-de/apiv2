import requests, os
from urllib.parse import urlencode
from breathecode.admissions.models import CohortUser
from .models import UserSpecialty, LayoutDesign
from ..services.google_cloud import Storage

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

    if cohort is None:
        cohorts = CohortUser.objects.filter(user__id=user.id)
        _count = cohorts.count()
        if _count == 1:
            _cohort = cohorts.first().cohort
            cohort = _cohort

    if cohort is None:
        raise Exception("Imposible to obtain the student cohort, maybe it has more than one or none assigned")

    if cohort.certificate is None:
        raise Exception(f"The cohort has no certificate assigned, please set a certificate for cohort: {cohort.name}")

    if cohort.certificate.specialty is None:
        raise Exception(f"Specialty has no certificate assigned, please set a certificate on the Specialty model: {cohort.certificate.name}")

    layout = LayoutDesign.objects.filter(slug='default').first()
    if layout is None:
        raise Exception("Missing a default layout")

    main_teacher = CohortUser.objects.filter(cohort__id=cohort.id, role='TEACHER').first()
    if main_teacher is None or main_teacher.user is None:
        raise Exception("This cohort does not have a main teacher, please assign it first")
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
    uspe.save()

    return uspe


def certificate_screenshot(certificate_id: int):

    # if ENVIRONMENT == 'development':
    #     return True

    certificate = UserSpecialty.objects.get(id=certificate_id)
    if certificate.preview_url is None or certificate.preview_url == "":
        file_name = f'{certificate.token}'
        # resolve_google_credentials()

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
        else:
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

import logging, json
from django.db.models.query_utils import Q
from .models import SyllabusVersion
from breathecode.services.google_cloud import Storage
from .signals import syllabus_asset_slug_updated

BUCKET_NAME = 'admissions-breathecode'
logger = logging.getLogger(__name__)


def get_bucket_object(file_name):
    if not file_name:
        return False

    storage = Storage()
    file = storage.file(BUCKET_NAME, file_name)
    return file.blob


def create_cohort_timeslot(certificate_timeslot, cohort_id):
    from breathecode.admissions.models import CohortTimeSlot
    cohort_timeslot = CohortTimeSlot(parent=certificate_timeslot,
                                     cohort_id=cohort_id,
                                     starting_at=certificate_timeslot.starting_at,
                                     ending_at=certificate_timeslot.ending_at,
                                     recurrent=certificate_timeslot.recurrent,
                                     recurrency_type=certificate_timeslot.recurrency_type)

    cohort_timeslot.save(force_insert=True)
    return cohort_timeslot


def update_cohort_timeslot(certificate_timeslot, cohort_timeslot):
    is_change = (cohort_timeslot.starting_at != certificate_timeslot.starting_at
                 or cohort_timeslot.ending_at != certificate_timeslot.ending_at
                 or cohort_timeslot.recurrent != certificate_timeslot.recurrent
                 or cohort_timeslot.recurrency_type != certificate_timeslot.recurrency_type)

    if not is_change:
        return

    cohort_timeslot.starting_at = certificate_timeslot.starting_at
    cohort_timeslot.ending_at = certificate_timeslot.ending_at
    cohort_timeslot.recurrent = certificate_timeslot.recurrent
    cohort_timeslot.recurrency_type = certificate_timeslot.recurrency_type

    cohort_timeslot.save()


def create_or_update_cohort_timeslot(certificate_timeslot):
    from breathecode.admissions.models import Cohort, CohortTimeSlot

    cohort_ids = Cohort.objects.filter(
        syllabus__certificate__id=certificate_timeslot.certificate.id)\
            .values_list('id', flat=True)

    for cohort_id in cohort_ids:
        cohort_timeslot = CohortTimeSlot.objects.filter(parent__id=certificate_timeslot.id,
                                                        cohort__id=cohort_id).first()

        if cohort_timeslot:
            update_cohort_timeslot(certificate_timeslot, cohort_timeslot)

        else:
            create_cohort_timeslot(certificate_timeslot, cohort_id)


def fill_cohort_timeslot(certificate_timeslot, cohort_id, timezone):
    from breathecode.admissions.models import CohortTimeSlot
    cohort_timeslot = CohortTimeSlot(cohort_id=cohort_id,
                                     starting_at=certificate_timeslot.starting_at,
                                     ending_at=certificate_timeslot.ending_at,
                                     recurrent=certificate_timeslot.recurrent,
                                     recurrency_type=certificate_timeslot.recurrency_type,
                                     timezone=timezone)

    return cohort_timeslot


def append_cohort_id_if_not_exist(cohort_timeslot):
    from breathecode.admissions.models import CohortTimeSlot

    if not cohort_timeslot.id:
        cohort_timeslot.id = CohortTimeSlot.objects.filter(
            created_at=cohort_timeslot.created_at,
            updated_at=cohort_timeslot.updated_at,
            cohort_id=cohort_timeslot.cohort_id,
            starting_at=cohort_timeslot.starting_at,
            ending_at=cohort_timeslot.ending_at,
            recurrent=cohort_timeslot.recurrent,
            recurrency_type=cohort_timeslot.recurrency_type,
            timezone=cohort_timeslot.timezone,
        ).values_list('id', flat=True).first()

    return cohort_timeslot


def sync_cohort_timeslots(cohort_id: int):
    from breathecode.admissions.models import SyllabusScheduleTimeSlot, CohortTimeSlot, Cohort
    CohortTimeSlot.objects.filter(cohort__id=cohort_id).delete()

    cohort_values = Cohort.objects.filter(id=cohort_id).values('academy__id', 'academy__timezone',
                                                               'schedule__id', 'slug').first()

    timezone = cohort_values['academy__timezone']
    if not timezone:
        slug = cohort_values['slug']
        logger.warning(f'Cohort `{slug}` was skipped because not have a timezone')
        return

    certificate_timeslots = SyllabusScheduleTimeSlot.objects.filter(
        Q(schedule__academy__id=cohort_values['academy__id']) | Q(schedule__syllabus__private=False),
        schedule__id=cohort_values['schedule__id'])

    timeslots = CohortTimeSlot.objects.bulk_create([
        fill_cohort_timeslot(certificate_timeslot, cohort_id, timezone)
        for certificate_timeslot in certificate_timeslots
    ])

    return [append_cohort_id_if_not_exist(x) for x in timeslots]


def post_cohort_change_syllabus_schedule(cohort_id: int):
    """
    Reset the CohortTimeSlot associate to a Cohort, this is thinking to be used in the POST or PUT serializer
    """

    from breathecode.admissions.models import CohortTimeSlot

    CohortTimeSlot.objects.filter(cohort__id=cohort_id).delete()
    return sync_cohort_timeslots(cohort_id)


def weeks_to_days(json):

    days = []
    weeks = json.pop('weeks', [])
    for week in weeks:
        days += week['days']

    if 'days' not in json:
        json['days'] = days

    return json


def update_asset_on_json(from_slug, to_slug, asset_type, simulate=True):

    asset_type = asset_type.upper()
    logger.debug(f'Replacing {asset_type} slug {from_slug} with {to_slug} in all the syllabus and versions')
    syllabus_list = SyllabusVersion.objects.all()
    key_map = {
        'QUIZ': 'quizzes',
        'LESSON': 'lessons',
        'EXERCISE': 'replits',
        'PROJECT': 'assignments',
    }

    findings = []
    for s in syllabus_list:
        moduleIndex = -1
        if isinstance(s.json, str):
            s.json = json.loads(s.json)

        # in case the json contains "weeks" instead of "days"
        s.json = weeks_to_days(s.json)

        for day in s.json['days']:
            moduleIndex += 1
            assetIndex = -1
            if key_map[asset_type] not in day:
                continue

            for a in day[key_map[asset_type]]:
                assetIndex += 1

                if isinstance(a, dict):
                    if a['slug'] == from_slug:
                        findings.append({
                            'module': moduleIndex,
                            'version': s.version,
                            'syllabus': s.syllabus.slug
                        })
                        s.json['days'][moduleIndex][key_map[asset_type]][assetIndex]['slug'] = to_slug
                else:
                    if a == from_slug:
                        findings.append({
                            'module': moduleIndex,
                            'version': s.version,
                            'syllabus': s.syllabus.slug
                        })
                        s.json['days'][moduleIndex][key_map[asset_type]][assetIndex] = to_slug
        if not simulate:
            s.save()

    if not simulate and len(findings) > 0:
        syllabus_asset_slug_updated.send(sender=update_asset_on_json,
                                         from_slug=from_slug,
                                         to_slug=to_slug,
                                         asset_type=asset_type)

    return findings

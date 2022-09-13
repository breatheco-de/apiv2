import logging, json
from django.db.models.query_utils import Q
from .models import Cohort, SyllabusScheduleTimeSlot, SyllabusVersion
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


class ImportCohortTimeSlots:
    cohort: Cohort

    def __init__(self, cohort_id: int) -> None:
        self.cohort = Cohort.objects.filter(id=cohort_id).first()

        if not self.cohort:
            logger.error(f'Cohort {cohort_id} not found')
            return

    def clean(self) -> None:
        from breathecode.admissions.models import CohortTimeSlot

        CohortTimeSlot.objects.filter(cohort=self.cohort).delete()

    def sync(self) -> None:
        from breathecode.admissions.models import SyllabusScheduleTimeSlot, CohortTimeSlot

        if not self.cohort:
            return

        timezone = self.cohort.timezone or self.cohort.academy.timezone
        if not timezone:
            slug = self.cohort.slug
            logger.warning(f'Cohort `{slug}` was skipped because not have a timezone')
            return

        certificate_timeslots = SyllabusScheduleTimeSlot.objects.filter(
            Q(schedule__academy__id=self.cohort.academy.id) | Q(schedule__syllabus__private=False),
            schedule__id=self.cohort.schedule.id)

        timeslots = CohortTimeSlot.objects.bulk_create([
            self._fill_timeslot(certificate_timeslot, self.cohort.id, timezone)
            for certificate_timeslot in certificate_timeslots
        ])

        return [self._append_id_of_timeslot(x) for x in timeslots]

    def _fill_timeslot(self, certificate_timeslot: SyllabusScheduleTimeSlot, cohort_id: int,
                       timezone: str) -> None:
        from breathecode.admissions.models import CohortTimeSlot

        cohort_timeslot = CohortTimeSlot(cohort_id=cohort_id,
                                         starting_at=certificate_timeslot.starting_at,
                                         ending_at=certificate_timeslot.ending_at,
                                         recurrent=certificate_timeslot.recurrent,
                                         recurrency_type=certificate_timeslot.recurrency_type,
                                         timezone=timezone)

        return cohort_timeslot

    def _append_id_of_timeslot(self, cohort_timeslot):
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


def weeks_to_days(json):

    days = []
    weeks = json.pop('weeks', [])
    for week in weeks:
        days += week['days']

    if 'days' not in json:
        json['days'] = days

    return json


def find_asset_on_json(asset_slug, asset_type=None):

    logger.debug(f'Searching slug {asset_slug} in all the syllabus and versions')
    syllabus_list = SyllabusVersion.objects.all()
    key_map = {
        'QUIZ': 'quizzes',
        'LESSON': 'lessons',
        'EXERCISE': 'replits',
        'PROJECT': 'assignments',
    }

    findings = []
    for s in syllabus_list:
        logger.debug(f'Starting with syllabus {s.syllabus.slug} version {str(s.version)}')
        moduleIndex = -1
        if isinstance(s.json, str):
            s.json = json.loads(s.json)

        # in case the json contains "weeks" instead of "days"
        s.json = weeks_to_days(s.json)

        for day in s.json['days']:
            moduleIndex += 1
            assetIndex = -1

            for atype in key_map:
                if key_map[atype] not in day or (asset_type is not None and atype != asset_type.upper()):
                    continue

                for a in day[key_map[atype]]:
                    assetIndex += 1

                    if isinstance(a, dict):
                        if a['slug'] == asset_slug:
                            findings.append({
                                'module': moduleIndex,
                                'version': s.version,
                                'type': atype,
                                'syllabus': s.syllabus.slug
                            })
                    else:
                        if a == asset_slug:
                            findings.append({
                                'module': moduleIndex,
                                'version': s.version,
                                'type': atype,
                                'syllabus': s.syllabus.slug
                            })

    return findings


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
        logger.debug(f'Starting with syllabus {s.syllabus.slug} version {str(s.version)}')
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


class SyllabusLog(object):
    errors = []
    warnings = []

    def error(self, msg):
        if len(self.errors) > 10:
            raise Exception('Too many errors on syllabus')

        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def concat(self, log):
        self.errors += log.errors
        self.warnings += log.warnings

    def serialize(self):
        return {'errors': self.errors, 'warnings': self.warnings}

    def http_status(self):
        if len(self.errors) == 0:
            return 200
        return 400


def test_syllabus(syl, validate_assets=False):
    from breathecode.registry.models import AssetAlias

    if isinstance(syl, str):
        syl = json.loads(syl)

    syllabus_log = SyllabusLog()
    if 'days' not in syl:
        syllabus_log.error("Syllabus must have a 'days' or 'modules' property")
        return syllabus_log

    def validate(_type, _log, day, index):
        if _type not in day:
            _log.error(f'Missing {_type} property on module {index}')
            return False
        for a in day[_type]:
            if 'slug' not in a:
                _log.error(f'Missing slug on {_type} property on module {index}')
            if not isinstance(a['slug'], str):
                _log.error(f'Slug property must be a string for {_type} on module {index}')

            if validate_assets:
                exists = AssetAlias.objects.filter(slug=a['slug']).first()
                if exists is None:
                    _log.error(f'Missing {_type} with slug {a["slug"]} on module {index}')
        return True

    count = 0

    for day in syl['days']:
        count += 1
        validate('lessons', syllabus_log, day, count)
        validate('quizzes', syllabus_log, day, count)
        validate('replits', syllabus_log, day, count)
        validate('projects', syllabus_log, day, count)
        if 'teacher_instructions' not in day or day['teacher_instructions'] == '':
            syllabus_log.warn(f'Empty teacher instructions on module {count}')

    print(f'Done...')
    return syllabus_log

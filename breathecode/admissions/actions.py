import json
import logging
from math import asin, cos, radians, sin, sqrt
from typing import Optional

from django.db.models.query_utils import Q

from breathecode.authenticate.models import User
from breathecode.services.google_cloud import Storage

from .models import Cohort, CohortUser, SyllabusScheduleTimeSlot, SyllabusVersion
from .signals import syllabus_asset_slug_updated

BUCKET_NAME = "admissions-breathecode"
logger = logging.getLogger(__name__)


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """

    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r


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
            logger.error(f"Cohort {cohort_id} not found")
            return

    def clean(self) -> None:
        from breathecode.admissions.models import CohortTimeSlot

        CohortTimeSlot.objects.filter(cohort=self.cohort).delete()

    def sync(self) -> None:
        from breathecode.admissions.models import CohortTimeSlot, SyllabusScheduleTimeSlot

        if not self.cohort:
            return

        timezone = self.cohort.timezone or self.cohort.academy.timezone
        if not timezone:
            slug = self.cohort.slug
            logger.warning(f"Cohort `{slug}` was skipped because not have a timezone")
            return

        certificate_timeslots = SyllabusScheduleTimeSlot.objects.filter(
            Q(schedule__academy__id=self.cohort.academy.id) | Q(schedule__syllabus__private=False),
            schedule__id=self.cohort.schedule.id,
        )

        timeslots = CohortTimeSlot.objects.bulk_create(
            [
                self._fill_timeslot(certificate_timeslot, self.cohort.id, timezone)
                for certificate_timeslot in certificate_timeslots
            ]
        )

        return [self._append_id_of_timeslot(x) for x in timeslots]

    def _fill_timeslot(self, certificate_timeslot: SyllabusScheduleTimeSlot, cohort_id: int, timezone: str) -> None:
        from breathecode.admissions.models import CohortTimeSlot

        cohort_timeslot = CohortTimeSlot(
            cohort_id=cohort_id,
            starting_at=certificate_timeslot.starting_at,
            ending_at=certificate_timeslot.ending_at,
            recurrent=certificate_timeslot.recurrent,
            recurrency_type=certificate_timeslot.recurrency_type,
            timezone=timezone,
        )

        return cohort_timeslot

    def _append_id_of_timeslot(self, cohort_timeslot):
        from breathecode.admissions.models import CohortTimeSlot

        if not cohort_timeslot.id:
            cohort_timeslot.id = (
                CohortTimeSlot.objects.filter(
                    created_at=cohort_timeslot.created_at,
                    updated_at=cohort_timeslot.updated_at,
                    cohort_id=cohort_timeslot.cohort_id,
                    starting_at=cohort_timeslot.starting_at,
                    ending_at=cohort_timeslot.ending_at,
                    recurrent=cohort_timeslot.recurrent,
                    recurrency_type=cohort_timeslot.recurrency_type,
                    timezone=cohort_timeslot.timezone,
                )
                .values_list("id", flat=True)
                .first()
            )

        return cohort_timeslot


def find_asset_on_json(asset_slug, asset_type=None):
    from breathecode.certificate.actions import syllabus_weeks_to_days

    logger.debug(f"Searching slug {asset_slug} in all the syllabus and versions")
    syllabus_list = SyllabusVersion.objects.all()
    key_map = {
        "QUIZ": "quizzes",
        "LESSON": "lessons",
        "EXERCISE": "replits",
        "PROJECT": "assignments",
    }

    findings = []
    for s in syllabus_list:
        logger.debug(f"Starting with syllabus {s.syllabus.slug} version {str(s.version)}")
        module_index = -1
        if isinstance(s.json, str):
            s.json = json.loads(s.json)

        # in case the json contains "weeks" instead of "days"
        s.json = syllabus_weeks_to_days(s.json)

        for day in s.json["days"]:
            module_index += 1
            asset_index = -1

            for atype in key_map:
                if key_map[atype] not in day or (asset_type is not None and atype != asset_type.upper()):
                    continue

                for a in day[key_map[atype]]:
                    asset_index += 1

                    if isinstance(a, dict):
                        if a["slug"] == asset_slug:
                            findings.append(
                                {
                                    "module": module_index,
                                    "version": s.version,
                                    "type": atype,
                                    "syllabus": s.syllabus.slug,
                                }
                            )
                    else:
                        if a == asset_slug:
                            findings.append(
                                {
                                    "module": module_index,
                                    "version": s.version,
                                    "type": atype,
                                    "syllabus": s.syllabus.slug,
                                }
                            )

    return findings


def update_asset_on_json(from_slug, to_slug, asset_type, simulate=True):
    from breathecode.certificate.actions import syllabus_weeks_to_days

    asset_type = asset_type.upper()
    logger.debug(f"Replacing {asset_type} slug {from_slug} with {to_slug} in all the syllabus and versions")
    syllabus_list = SyllabusVersion.objects.all()
    key_map = {
        "QUIZ": "quizzes",
        "LESSON": "lessons",
        "EXERCISE": "replits",
        "PROJECT": "assignments",
    }

    findings = []
    for s in syllabus_list:
        logger.debug(f"Starting with syllabus {s.syllabus.slug} version {str(s.version)}")
        module_index = -1
        if isinstance(s.json, str):
            s.json = json.loads(s.json)

        # in case the json contains "weeks" instead of "days"
        s.json = syllabus_weeks_to_days(s.json)

        for day in s.json["days"]:
            module_index += 1
            asset_index = -1
            if key_map[asset_type] not in day:
                continue

            for a in day[key_map[asset_type]]:
                asset_index += 1

                if isinstance(a, dict):
                    if a["slug"] == from_slug:
                        findings.append({"module": module_index, "version": s.version, "syllabus": s.syllabus.slug})
                        s.json["days"][module_index][key_map[asset_type]][asset_index]["slug"] = to_slug
                else:
                    if a == from_slug:
                        findings.append({"module": module_index, "version": s.version, "syllabus": s.syllabus.slug})
                        s.json["days"][module_index][key_map[asset_type]][asset_index] = to_slug
        if not simulate:
            s.save()

    if not simulate and len(findings) > 0:
        syllabus_asset_slug_updated.send_robust(
            sender=update_asset_on_json, from_slug=from_slug, to_slug=to_slug, asset_type=asset_type
        )

    return findings


class SyllabusLog(object):
    errors = []
    warnings = []

    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg):
        if len(self.errors) == 10:
            self.errors.append("Can only log first 10 errors on syllabus")
        if len(self.errors) > 10:
            return None

        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def concat(self, log):
        self.errors += log.errors
        self.warnings += log.warnings

    def serialize(self):
        return {"errors": self.errors, "warnings": self.warnings}

    def http_status(self):
        if len(self.errors) == 0:
            return 200
        return 400


def test_syllabus(syl, validate_assets=False, ignore=None):
    from breathecode.registry.models import AssetAlias

    if ignore is None:
        ignore = []

    if isinstance(syl, str):
        syl = json.loads(syl)

    syllabus_log = SyllabusLog()
    if "days" not in syl:
        syllabus_log.error("Syllabus must have a 'days' or 'modules' property")
        return syllabus_log

    def validate(_type, _log, day, index):
        if _type not in day:
            _log.error(f"Missing {_type} property on module {index}")
            return False
        for a in day[_type]:
            if "slug" not in a:
                _log.error(f"Missing slug on {_type} property on module {index}")
            if not isinstance(a["slug"], str):
                _log.error(f"Slug property must be a string for {_type} on module {index}")

            if validate_assets:
                exists = AssetAlias.objects.filter(slug=a["slug"]).first()
                if exists is None and not ("target" in a and a["target"] == "blank"):
                    _log.error(f'Missing {_type} with slug {a["slug"]} on module {index}')
        return True

    count = 0

    types_to_validate = ["lessons", "quizzes", "replits", "assignments"]

    # ignore: an array with types to ignore, for example: ['lessons']
    types_to_validate = [a for a in types_to_validate if a not in ignore]
    for day in syl["days"]:
        count += 1
        for _name in types_to_validate:
            validate(_name, syllabus_log, day, count)
        if "teacher_instructions" not in day or day["teacher_instructions"] == "":
            syllabus_log.warn(f"Empty teacher instructions on module {count}")
        if len(syllabus_log.errors) > 11:
            return syllabus_log

    return syllabus_log


def is_no_saas_student_up_to_date_in_any_cohort(
    user: User, cohort: Optional[Cohort] = None, academy: Optional[Cohort] = None, default: bool = True
) -> str:
    no_available_as_saas = Q(cohort__available_as_saas=False) | Q(
        cohort__available_as_saas=None, cohort__academy__available_as_saas=False
    )

    extra = {}
    if cohort:
        extra["cohort"] = cohort

    if academy:
        extra["cohort__academy"] = academy

    if (
        cohort is None
        and CohortUser.objects.filter(
            no_available_as_saas, user=user, educational_status__in=["ACTIVE", "GRADUATED"], **extra
        )
        .exclude(finantial_status="LATE")
        .exists()
    ):
        return True

    if CohortUser.objects.filter(
        no_available_as_saas, user=user, finantial_status="LATE", educational_status="ACTIVE", **extra
    ).exists():
        return False

    # if no cohorts were found, we assume that the user is up to date
    return default

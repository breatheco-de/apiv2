import json
import logging
from math import asin, cos, radians, sin, sqrt
from typing import Any, Iterator, Optional

from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from django.db.models import Max, Min
from django.db.models.functions import Coalesce
from django.db.models.query_utils import Q

from breathecode.authenticate.models import User
from breathecode.certificate.actions import get_assets_from_syllabus
from breathecode.certificate.models import UserSpecialty
from breathecode.assignments.models import Task
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
        from breathecode.events.models import LiveClass
        from django.db.models import Q

        if not self.cohort:
            return

        # Delete all timeslots for this cohort
        CohortTimeSlot.objects.filter(cohort=self.cohort).delete()

        # Delete all live classes associated with this cohort
        # This includes:
        # 1. Live classes linked via cohort_time_slot (already deleted by CASCADE, but handle edge cases)
        # 2. Live classes directly linked via cohort field
        LiveClass.objects.filter(Q(cohort_time_slot__cohort=self.cohort) | Q(cohort=self.cohort)).delete()

    def sync(self) -> None:
        from breathecode.admissions.models import CohortTimeSlot, SyllabusScheduleTimeSlot

        if not self.cohort:
            return

        # Guard: If schedule is None, no timeslots to sync
        if not self.cohort.schedule:
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


def _get_enrollments_for_academy_student_progress_report(academy):
    return (
        CohortUser.objects.filter(cohort__academy=academy, role="STUDENT")
        .select_related("user", "cohort", "cohort__syllabus_version", "cohort__syllabus_version__syllabus")
        .prefetch_related("cohort__micro_cohorts")
        .order_by("cohort_id", "created_at")
    )


def _build_syllabus_cache_by_cohort(cohorts: list[Cohort]) -> tuple[
    dict[int, set[str]],
    dict[int, set[str]],
    dict[int, int],
    dict[int, set[str]],
    dict[int, bool],
]:
    lesson_slugs_by_cohort: dict[int, set[str]] = {}
    exercise_slugs_by_cohort: dict[int, set[str]] = {}
    total_lessons_by_cohort: dict[int, int] = {}
    mandatory_project_slugs_by_cohort: dict[int, set[str]] = {}
    has_mandatory_projects_by_cohort: dict[int, bool] = {}

    for cohort in cohorts:
        if cohort is None or cohort.syllabus_version is None:
            # Defensive: cohort should never be None, but keep it safe.
            continue

        if cohort.syllabus_version is None:
            lesson_slugs_by_cohort[cohort.id] = set()
            exercise_slugs_by_cohort[cohort.id] = set()
            total_lessons_by_cohort[cohort.id] = 0
            mandatory_project_slugs_by_cohort[cohort.id] = set()
            has_mandatory_projects_by_cohort[cohort.id] = False
            continue

        lesson_slugs = get_assets_from_syllabus(cohort.syllabus_version, task_types=["LESSON"], only_mandatory=False) or []
        exercise_slugs = get_assets_from_syllabus(cohort.syllabus_version, task_types=["EXERCISE"], only_mandatory=False) or []
        mandatory_project_slugs = (
            get_assets_from_syllabus(cohort.syllabus_version, task_types=["PROJECT"], only_mandatory=True) or []
        )

        lesson_slugs_by_cohort[cohort.id] = set(lesson_slugs)
        exercise_slugs_by_cohort[cohort.id] = set(exercise_slugs)
        total_lessons_by_cohort[cohort.id] = len(lesson_slugs)
        mandatory_project_slugs_by_cohort[cohort.id] = set(mandatory_project_slugs)
        has_mandatory_projects_by_cohort[cohort.id] = len(mandatory_project_slugs) > 0

    return (
        lesson_slugs_by_cohort,
        exercise_slugs_by_cohort,
        total_lessons_by_cohort,
        mandatory_project_slugs_by_cohort,
        has_mandatory_projects_by_cohort,
    )


def _parse_history_log_for_report(enrollments: list[CohortUser]) -> tuple[dict[tuple[int, int], list[int]], dict[tuple[int, int], bool]]:
    delivered_exercise_task_ids_by_pair: dict[tuple[int, int], list[int]] = {}
    started_by_pair: dict[tuple[int, int], bool] = {}

    for cu in enrollments:
        h = cu.history_log or {}
        delivered = h.get("delivered_assignments", []) or []
        pending = h.get("pending_assignments", []) or []

        pair = (cu.user_id, cu.cohort_id)
        started_by_pair[pair] = bool(delivered or pending)

        exercise_ids = [
            int(x["id"])
            for x in delivered
            if isinstance(x, dict) and x.get("type") == "EXERCISE" and str(x.get("id", "")).isdigit()
        ]
        if exercise_ids:
            delivered_exercise_task_ids_by_pair[pair] = exercise_ids

    return delivered_exercise_task_ids_by_pair, started_by_pair


def _get_delivered_tasks_by_id(task_ids: list[int], user_ids: list[int], cohort_ids: list[int]) -> dict[int, dict]:
    if not task_ids:
        return {}

    rows = (
        Task.objects.filter(id__in=task_ids, user_id__in=user_ids, cohort_id__in=cohort_ids)
        .values("id", "user_id", "cohort_id", "task_type", "associated_slug")
    )
    return {r["id"]: r for r in rows}


def _get_delivered_exercise_slugs_by_pair(
    delivered_exercise_task_ids_by_pair: dict[tuple[int, int], list[int]],
    delivered_tasks_by_id: dict[int, dict],
    exercise_slugs_by_cohort: dict[int, set[str]],
) -> dict[tuple[int, int], set[str]]:
    delivered_exercise_slugs_by_pair: dict[tuple[int, int], set[str]] = {}

    for pair, ids in delivered_exercise_task_ids_by_pair.items():
        _user_id, cohort_id = pair
        syllabus_exercise_slugs = exercise_slugs_by_cohort.get(cohort_id, set())
        if not syllabus_exercise_slugs:
            delivered_exercise_slugs_by_pair[pair] = set()
            continue

        slugs: set[str] = set()
        for tid in ids:
            t = delivered_tasks_by_id.get(tid)
            if not t:
                continue
            if t["associated_slug"] in syllabus_exercise_slugs:
                slugs.add(t["associated_slug"])

        delivered_exercise_slugs_by_pair[pair] = slugs

    return delivered_exercise_slugs_by_pair


def _get_lesson_done_slugs_by_pair(
    user_ids: list[int], cohort_ids: list[int], lesson_slugs_by_cohort: dict[int, set[str]]
) -> dict[tuple[int, int], set[str]]:
    all_lesson_slugs: set[str] = set()
    for slugs in lesson_slugs_by_cohort.values():
        all_lesson_slugs.update(slugs)

    lesson_done_slugs_by_pair: dict[tuple[int, int], set[str]] = {}
    if not all_lesson_slugs:
        return lesson_done_slugs_by_pair

    done_lessons = Task.objects.filter(
        user_id__in=user_ids,
        cohort_id__in=cohort_ids,
        task_type=Task.TaskType.LESSON,
        task_status=Task.TaskStatus.DONE,
        associated_slug__in=list(all_lesson_slugs),
    ).values("user_id", "cohort_id", "associated_slug")

    for r in done_lessons:
        pair = (r["user_id"], r["cohort_id"])
        if pair not in lesson_done_slugs_by_pair:
            lesson_done_slugs_by_pair[pair] = set()
        lesson_done_slugs_by_pair[pair].add(r["associated_slug"])

    return lesson_done_slugs_by_pair


def _get_student_start_date_by_pair(
    user_ids: list[int],
    cohort_ids: list[int],
    lesson_slugs_by_cohort: dict[int, set[str]],
    exercise_slugs_by_cohort: dict[int, set[str]],
) -> dict[tuple[int, int], object]:
    relevant_slugs: set[str] = set()
    for cid in cohort_ids:
        relevant_slugs.update(lesson_slugs_by_cohort.get(cid, set()))
        relevant_slugs.update(exercise_slugs_by_cohort.get(cid, set()))

    if not relevant_slugs:
        return {}

    started_rows = (
        Task.objects.filter(
            user_id__in=user_ids,
            cohort_id__in=cohort_ids,
            associated_slug__in=list(relevant_slugs),
            task_type__in=[Task.TaskType.LESSON, Task.TaskType.EXERCISE],
        )
        .values("user_id", "cohort_id")
        .annotate(started_at=Min(Coalesce("opened_at", "delivered_at", "created_at")))
    )
    return {(r["user_id"], r["cohort_id"]): r["started_at"] for r in started_rows}


def _telemetry_to_steps(telemetry: dict) -> tuple[int, int]:
    if not isinstance(telemetry, dict):
        return 0, 0

    global_metrics = telemetry.get("global_metrics")
    if isinstance(global_metrics, dict):
        total_steps = int(global_metrics.get("total_steps") or 0)
        if total_steps > 0:
            completion_rate = global_metrics.get("completion_rate")
            if completion_rate is not None:
                try:
                    cr = float(completion_rate)
                    completed = int(round((cr / 100.0) * total_steps))
                    completed = 0 if completed < 0 else completed
                    completed = total_steps if completed > total_steps else completed
                    return total_steps, completed
                except Exception:
                    pass

            steps_not_completed = int(global_metrics.get("steps_not_completed") or 0)
            completed = total_steps - steps_not_completed
            completed = 0 if completed < 0 else completed
            completed = total_steps if completed > total_steps else completed
            return total_steps, completed

    return 0, 0


def _get_completed_exercise_slugs_by_pair(
    user_ids: list[int],
    cohort_ids: list[int],
    exercise_slugs_by_cohort: dict[int, set[str]],
    delivered_exercise_slugs_by_pair: dict[tuple[int, int], set[str]],
) -> dict[tuple[int, int], set[str]]:
    all_exercise_slugs: set[str] = set()
    for slugs in exercise_slugs_by_cohort.values():
        all_exercise_slugs.update(slugs)

    completed_exercise_slugs_by_pair: dict[tuple[int, int], set[str]] = {}
    if not all_exercise_slugs:
        return completed_exercise_slugs_by_pair

    # Telemetry-based completion (completion_rate == 100).
    telemetry_rows = Task.objects.filter(
        user_id__in=user_ids,
        cohort_id__in=cohort_ids,
        task_type=Task.TaskType.EXERCISE,
        associated_slug__in=list(all_exercise_slugs),
        telemetry__isnull=False,
    ).values("user_id", "cohort_id", "associated_slug", "telemetry__telemetry")

    telemetry_by_triplet: dict[tuple[int, int, str], dict] = {}
    for t in telemetry_rows:
        key = (t["user_id"], t["cohort_id"], t["associated_slug"])
        if key in telemetry_by_triplet:
            continue
        telemetry = t.get("telemetry__telemetry")
        if isinstance(telemetry, dict):
            telemetry_by_triplet[key] = telemetry

    for (user_id, cohort_id, slug), telemetry in telemetry_by_triplet.items():
        total_steps, completed_steps = _telemetry_to_steps(telemetry)
        if total_steps <= 0:
            continue
        if completed_steps >= total_steps:
            pair = (user_id, cohort_id)
            if pair not in completed_exercise_slugs_by_pair:
                completed_exercise_slugs_by_pair[pair] = set()
            completed_exercise_slugs_by_pair[pair].add(slug)

    # Task status DONE.
    done_exercises = Task.objects.filter(
        user_id__in=user_ids,
        cohort_id__in=cohort_ids,
        task_type=Task.TaskType.EXERCISE,
        task_status=Task.TaskStatus.DONE,
        associated_slug__in=list(all_exercise_slugs),
    ).values("user_id", "cohort_id", "associated_slug")

    for r in done_exercises:
        pair = (r["user_id"], r["cohort_id"])
        if pair not in completed_exercise_slugs_by_pair:
            completed_exercise_slugs_by_pair[pair] = set()
        completed_exercise_slugs_by_pair[pair].add(r["associated_slug"])

    # history_log delivered (best-effort).
    for pair, slugs in delivered_exercise_slugs_by_pair.items():
        if not slugs:
            continue
        if pair not in completed_exercise_slugs_by_pair:
            completed_exercise_slugs_by_pair[pair] = set()
        completed_exercise_slugs_by_pair[pair].update(slugs)

    return completed_exercise_slugs_by_pair


def _get_cert_by_pair(academy, user_ids: list[int], cohort_ids: list[int]) -> dict[tuple[int, int], dict]:
    cert_rows = (
        UserSpecialty.objects.filter(user_id__in=user_ids, cohort_id__in=cohort_ids, academy=academy)
        .exclude(status="ERROR")
        .values("user_id", "cohort_id", "token", "issued_at", "preview_url", "status")
    )
    return {(r["user_id"], r["cohort_id"]): r for r in cert_rows}


def _get_approved_mandatory_project_slugs_by_pair(
    user_ids: list[int], cohort_ids: list[int], mandatory_project_slugs_by_cohort: dict[int, set[str]]
) -> dict[tuple[int, int], set[str]]:
    mandatory_project_slugs_union: set[str] = set()
    for slugs in mandatory_project_slugs_by_cohort.values():
        mandatory_project_slugs_union.update(slugs)

    approved_mandatory_project_slugs_by_pair: dict[tuple[int, int], set[str]] = {}
    if not mandatory_project_slugs_union:
        return approved_mandatory_project_slugs_by_pair

    approved_rows = Task.objects.filter(
        user_id__in=user_ids,
        cohort_id__in=cohort_ids,
        task_type=Task.TaskType.PROJECT,
        associated_slug__in=list(mandatory_project_slugs_union),
        revision_status__in=[Task.RevisionStatus.APPROVED, Task.RevisionStatus.IGNORED],
    ).values("user_id", "cohort_id", "associated_slug")

    for r in approved_rows:
        pair = (r["user_id"], r["cohort_id"])
        if pair not in approved_mandatory_project_slugs_by_pair:
            approved_mandatory_project_slugs_by_pair[pair] = set()
        approved_mandatory_project_slugs_by_pair[pair].add(r["associated_slug"])

    return approved_mandatory_project_slugs_by_pair


def _get_completion_date_by_pair(
    user_ids: list[int],
    cohort_ids: list[int],
    lesson_slugs_by_cohort: dict[int, set[str]],
    exercise_slugs_by_cohort: dict[int, set[str]],
) -> dict[tuple[int, int], object]:
    relevant_slugs: set[str] = set()
    for cid in cohort_ids:
        relevant_slugs.update(lesson_slugs_by_cohort.get(cid, set()))
        relevant_slugs.update(exercise_slugs_by_cohort.get(cid, set()))

    if not relevant_slugs:
        return {}

    completion_rows = (
        Task.objects.filter(
            user_id__in=user_ids,
            cohort_id__in=cohort_ids,
            task_type__in=[Task.TaskType.LESSON, Task.TaskType.EXERCISE],
            task_status=Task.TaskStatus.DONE,
            associated_slug__in=list(relevant_slugs),
        )
        .values("user_id", "cohort_id")
        .annotate(completion_date=Max("updated_at"))
    )
    return {(r["user_id"], r["cohort_id"]): r["completion_date"] for r in completion_rows}


def _map_status_for_student_progress(cu: CohortUser, *, started: bool, is_completed: bool) -> str:
    edu = (cu.educational_status or "").upper()
    if edu in ("DROPPED", "NOT_COMPLETING", "SUSPENDED"):
        return "withdrawn"
    if is_completed:
        return "completed"
    if not started:
        return "not_started"
    return "in_progress"


def _progress_percent(total_units: int, completed_units: int) -> tuple[int, bool]:
    if total_units <= 0:
        return 0, False

    ratio = (completed_units / total_units) * 100.0
    is_completed = ratio >= 99.99
    progress = int(round(ratio))
    progress = 0 if progress < 0 else progress
    progress = 100 if progress > 100 else progress
    if is_completed:
        progress = 100
    return progress, is_completed


def academy_student_progress_report_rows(academy, lang: str, cohort: Optional[Cohort] = None) -> Iterator[list]:
    """
    Build rows for the Academy student progress report (CSV).

    Output columns:
    - course_name
    - student_full_name
    - student_email
    - enrollment_date
    - student_start_date
    - status (not_started / in_progress / completed / withdrawn)
    - progress_percentage (0-100)
    - completion_date
    - certificate_url
    - comments
    """

    if academy is None:
        raise ValidationException(
            translation(
                lang,
                en="Academy not found",
                es="Academia no encontrada",
                slug="academy-not-found",
            ),
            slug="academy-not-found",
        )

    enrollments_qs = _get_enrollments_for_academy_student_progress_report(academy)
    if cohort is not None:
        enrollments_qs = enrollments_qs.filter(cohort=cohort)
    if not enrollments_qs.exists():
        return iter([])

    enrollments = list(enrollments_qs)
    user_ids = list({cu.user_id for cu in enrollments})
    cohort_ids = list({cu.cohort_id for cu in enrollments})

    cohorts_by_id = {cu.cohort_id: cu.cohort for cu in enrollments if cu.cohort is not None}

    (
        lesson_slugs_by_cohort,
        exercise_slugs_by_cohort,
        total_lessons_by_cohort,
        mandatory_project_slugs_by_cohort,
        has_mandatory_projects_by_cohort,
    ) = _build_syllabus_cache_by_cohort(list(cohorts_by_id.values()))

    delivered_exercise_task_ids_by_pair, started_by_pair = _parse_history_log_for_report(enrollments)
    task_ids = [tid for ids in delivered_exercise_task_ids_by_pair.values() for tid in ids]
    delivered_tasks_by_id = _get_delivered_tasks_by_id(task_ids, user_ids, cohort_ids)
    delivered_exercise_slugs_by_pair = _get_delivered_exercise_slugs_by_pair(
        delivered_exercise_task_ids_by_pair, delivered_tasks_by_id, exercise_slugs_by_cohort
    )

    lesson_done_slugs_by_pair = _get_lesson_done_slugs_by_pair(user_ids, cohort_ids, lesson_slugs_by_cohort)
    started_at_by_pair = _get_student_start_date_by_pair(user_ids, cohort_ids, lesson_slugs_by_cohort, exercise_slugs_by_cohort)
    completed_exercise_slugs_by_pair = _get_completed_exercise_slugs_by_pair(
        user_ids, cohort_ids, exercise_slugs_by_cohort, delivered_exercise_slugs_by_pair
    )
    cert_by_pair = _get_cert_by_pair(academy, user_ids, cohort_ids)
    approved_mandatory_project_slugs_by_pair = _get_approved_mandatory_project_slugs_by_pair(
        user_ids, cohort_ids, mandatory_project_slugs_by_cohort
    )
    completion_date_by_pair = _get_completion_date_by_pair(user_ids, cohort_ids, lesson_slugs_by_cohort, exercise_slugs_by_cohort)

    def _get_units_for(user_id: int, cohort_id: int) -> tuple[int, int]:
        total_lessons = int(total_lessons_by_cohort.get(cohort_id, 0))
        completed_lessons = len(
            (lesson_done_slugs_by_pair.get((user_id, cohort_id), set()) or set())
            & (lesson_slugs_by_cohort.get(cohort_id, set()) or set())
        )
        total_exercises = len(exercise_slugs_by_cohort.get(cohort_id, set()))

        completed_exercises = len(
            (completed_exercise_slugs_by_pair.get((user_id, cohort_id), set()) or set())
            & (exercise_slugs_by_cohort.get(cohort_id, set()) or set())
        )

        total_units = total_lessons + total_exercises
        completed_units = completed_lessons + completed_exercises

        if total_units and completed_units > total_units:
            completed_units = total_units
        if completed_units < 0:
            completed_units = 0

        return total_units, completed_units

    rows_to_write: list[dict[str, Any]] = []

    expected_slugs_union: set[str] = set()
    for cid in cohort_ids:
        expected_slugs_union.update(lesson_slugs_by_cohort.get(cid, set()))
        expected_slugs_union.update(exercise_slugs_by_cohort.get(cid, set()))

    tasks_any_by_pair: set[tuple[int, int]] = set()
    if expected_slugs_union:
        any_rows = Task.objects.filter(
            user_id__in=user_ids,
            cohort_id__in=cohort_ids,
            associated_slug__in=list(expected_slugs_union),
        ).values("user_id", "cohort_id")
        tasks_any_by_pair = {(r["user_id"], r["cohort_id"]) for r in any_rows}

    cohort_ids_by_user: dict[int, set[int]] = {}
    for cu in enrollments:
        if cu.user_id not in cohort_ids_by_user:
            cohort_ids_by_user[cu.user_id] = set()
        cohort_ids_by_user[cu.user_id].add(cu.cohort_id)

    for cu in enrollments:
        user = cu.user
        cohort = cu.cohort

        course_name = getattr(cohort, "name", "") if cohort else ""
        full_name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip() if user else ""
        email = getattr(user, "email", "") if user else ""

        pair = (cu.user_id, cu.cohort_id)

        student_start_date = started_at_by_pair.get(pair)
        edu = (cu.educational_status or "").upper()

        is_macro = bool(cohort and hasattr(cohort, "micro_cohorts") and cohort.micro_cohorts.exists())
        if is_macro:
            course_name = f"{course_name} (Macro cohort)"

            user_cohorts = cohort_ids_by_user.get(cu.user_id, set())
            micro_ids = [c.id for c in cohort.micro_cohorts.all() if c.id in user_cohorts]

            total_units = 0
            completed_units = 0
            macro_started = False
            macro_started_at = None

            for micro_id in micro_ids:
                micro_total, micro_completed = _get_units_for(cu.user_id, micro_id)
                total_units += micro_total
                completed_units += micro_completed

                if (cu.user_id, micro_id) in tasks_any_by_pair or started_by_pair.get((cu.user_id, micro_id), False):
                    macro_started = True

                micro_started_at = started_at_by_pair.get((cu.user_id, micro_id))
                if micro_started_at and (macro_started_at is None or micro_started_at < macro_started_at):
                    macro_started_at = micro_started_at

            student_start_date = macro_started_at or student_start_date
            progress, is_completed = _progress_percent(total_units, completed_units)
            started = macro_started

            is_certificate_eligible = (
                any(has_mandatory_projects_by_cohort.get(mid, False) for mid in micro_ids) if micro_ids else False
            )
        else:
            total_units, completed_units = _get_units_for(cu.user_id, cu.cohort_id)
            progress, is_completed = _progress_percent(total_units, completed_units)
            started = bool((pair in tasks_any_by_pair) or started_by_pair.get(pair, False))
            is_certificate_eligible = bool(has_mandatory_projects_by_cohort.get(cu.cohort_id, False))

        if edu == "GRADUATED":
            progress = 100
            is_completed = True

        status_value = _map_status_for_student_progress(cu, started=started, is_completed=is_completed)

        cert = cert_by_pair.get(pair)
        completion_date = None
        certificate_url = None
        if cert and cert.get("token"):
            certificate_url = f"https://certificate.4geeks.com/{cert.get('token')}"

        comments = ""
        if total_units == 0 and status_value != "completed":
            comments = translation(
                lang,
                en="No syllabus lessons found and no learnpack telemetry; progress estimated as 0",
                es="No se encontraron lecciones en el syllabus y no hay telemetry de learnpacks; progreso estimado en 0",
                slug="no-lessons-or-telemetry",
            )

        if not is_certificate_eligible:
            no_cert_msg = translation(
                lang,
                en="This cohort does not include mandatory projects; certificates are not issued for it",
                es="Esta cohorte no incluye proyectos obligatorios; no se emiten certificados para ella",
                slug="no-mandatory-projects-no-certificate",
            )
            comments = (comments + " | " if comments else "") + no_cert_msg
        else:
            if progress >= 100 and cert is None:
                pending_mandatory = 0
                if is_macro:
                    for micro_id in micro_ids:
                        required = mandatory_project_slugs_by_cohort.get(micro_id, set())
                        if not required:
                            continue
                        approved = approved_mandatory_project_slugs_by_pair.get((cu.user_id, micro_id), set())
                        pending_mandatory += len(required - approved)
                else:
                    required = mandatory_project_slugs_by_cohort.get(cu.cohort_id, set())
                    approved = approved_mandatory_project_slugs_by_pair.get(pair, set())
                    pending_mandatory = len(required - approved) if required else 0

                if pending_mandatory > 0:
                    proj_msg = translation(
                        lang,
                        en=f"Progress is 100% for lessons/exercises, but {pending_mandatory} mandatory project(s) are still pending; certificate not generated yet",
                        es=f"El progreso es 100% en lecciones/ejercicios, pero faltan {pending_mandatory} proyecto(s) obligatorio(s); el certificado aún no se ha generado",
                        slug="pending-mandatory-projects-no-certificate-yet",
                    )
                    comments = (comments + " | " if comments else "") + proj_msg

        rows_to_write.append(
            {
                "pair": pair,
                "course_name": course_name,
                "full_name": full_name,
                "email": email,
                "enrollment_date": cu.created_at,
                "student_start_date": student_start_date,
                "status": status_value,
                "progress": progress,
                "completion_date": completion_date,
                "certificate_url": certificate_url,
                "comments": comments,
                "edu": edu,
            }
        )

    for item in rows_to_write:
        if item["progress"] >= 100:
            user_id, cohort_id = item["pair"]
            cohort = cohorts_by_id.get(cohort_id)
            is_macro = bool(cohort and hasattr(cohort, "micro_cohorts") and cohort.micro_cohorts.exists())
            if is_macro:
                user_cohorts = cohort_ids_by_user.get(user_id, set())
                micro_ids = [c.id for c in cohort.micro_cohorts.all() if c.id in user_cohorts]
                best = None
                for micro_id in micro_ids:
                    d = completion_date_by_pair.get((user_id, micro_id))
                    if d and (best is None or d > best):
                        best = d
                item["completion_date"] = best
            else:
                item["completion_date"] = completion_date_by_pair.get((user_id, cohort_id))

        yield [
            item["course_name"],
            item["full_name"],
            item["email"],
            item["enrollment_date"],
            item["student_start_date"],
            item["status"],
            item["progress"],
            item["completion_date"],
            item["certificate_url"],
            item["comments"],
        ]


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

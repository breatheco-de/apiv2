from __future__ import annotations

import json
from dataclasses import dataclass
from logging import getLogger
from typing import Any

from django.core.cache import cache

from breathecode.admissions.actions import resolve_syllabus_json
from breathecode.admissions.models import CohortUser, SyllabusVersion
from breathecode.assignments.models import Task

FULL_COMPLETION = "FULL_COMPLETION"
PARTIAL_COMPLETION = "PARTIAL_COMPLETION"
LEGACY_PROJECTS = "LEGACY_PROJECTS"
NO_COMPLETION_STRATEGY = "NO_COMPLETION_STRATEGY"
COMPLETION_CACHE_TTL_SECONDS = 60 * 10
logger = getLogger(__name__)

TASK_TYPES = ("PROJECT", "EXERCISE", "LESSON", "QUIZ")
SYLLABUS_KEY_BY_TASK_TYPE = {
    "QUIZ": "quizzes",
    "LESSON": "lessons",
    "EXERCISE": "replits",
    "PROJECT": "assignments",
}


@dataclass(frozen=True)
class CompletionRequirement:
    task_type: str
    min_percent: float
    only_mandatory: bool = False


def _normalize_percent(value: Any, default: float = 100) -> float:
    try:
        percent = float(value)
    except (TypeError, ValueError):
        percent = default

    if percent < 0:
        return 0
    if percent > 100:
        return 100
    return percent


def _load_syllabus_json(
    syllabus_version: SyllabusVersion | int | None,
    *,
    macro_syllabus_json: dict | str | None = None,
    syllabus_slug: str | None = None,
    syllabus_version_number: int | str | None = None,
) -> dict:
    if syllabus_version is None:
        return {"days": []}

    if not isinstance(syllabus_version, SyllabusVersion):
        syllabus_version = SyllabusVersion.objects.filter(id=syllabus_version).first()
        if syllabus_version is None:
            return {"days": []}

    syllabus_json = syllabus_version.json or {"days": []}
    if isinstance(syllabus_json, str):
        syllabus_json = json.loads(syllabus_json)

    return resolve_syllabus_json(
        syllabus_json,
        macro_syllabus_json=macro_syllabus_json,
        syllabus_slug=syllabus_slug,
        syllabus_version=syllabus_version_number,
    )


def _override_kwargs_from_cohort_user(cohort_user: CohortUser) -> dict | None:
    source_macro = cohort_user.source_macro_cohort
    cohort = cohort_user.cohort
    micro_version = cohort.syllabus_version if cohort else None
    macro_version = source_macro.syllabus_version if source_macro else None
    if source_macro is None or micro_version is None or macro_version is None or micro_version.syllabus is None:
        return None

    return {
        "macro_syllabus_json": macro_version.json,
        "syllabus_slug": micro_version.syllabus.slug,
        "syllabus_version_number": micro_version.version,
    }


def get_syllabus_assets_by_type(
    syllabus_version: SyllabusVersion | int | None,
    *,
    task_types: list[str] | tuple[str, ...] | None = None,
    only_mandatory: bool = False,
    macro_syllabus_json: dict | str | None = None,
    syllabus_slug: str | None = None,
    syllabus_version_number: int | str | None = None,
) -> dict[str, set[str]]:
    syllabus_json = _load_syllabus_json(
        syllabus_version,
        macro_syllabus_json=macro_syllabus_json,
        syllabus_slug=syllabus_slug,
        syllabus_version_number=syllabus_version_number,
    )
    task_types = tuple(task_types or TASK_TYPES)
    assets_by_type: dict[str, set[str]] = {task_type: set() for task_type in task_types}

    for day in syllabus_json.get("days", []):
        for task_type in task_types:
            key = SYLLABUS_KEY_BY_TASK_TYPE.get(task_type)
            if not key:
                continue

            for asset in day.get(key, []):
                if only_mandatory and not asset.get("mandatory", True):
                    continue

                slug = asset.get("slug")
                if slug:
                    assets_by_type.setdefault(task_type, set()).add(slug)

    return assets_by_type


def get_assets_from_syllabus(
    syllabus_version: SyllabusVersion | int | None,
    *,
    task_types: list[str] | tuple[str, ...] | None = None,
    only_mandatory: bool = False,
    macro_syllabus_json: dict | str | None = None,
    syllabus_slug: str | None = None,
    syllabus_version_number: int | str | None = None,
) -> list[str]:
    assets_by_type = get_syllabus_assets_by_type(
        syllabus_version,
        task_types=task_types,
        only_mandatory=only_mandatory,
        macro_syllabus_json=macro_syllabus_json,
        syllabus_slug=syllabus_slug,
        syllabus_version_number=syllabus_version_number,
    )
    slugs: list[str] = []
    for task_type in task_types or TASK_TYPES:
        slugs.extend(sorted(assets_by_type.get(task_type, set())))
    return slugs


def get_completion_strategy(
    syllabus_version: SyllabusVersion | int | None,
    *,
    macro_syllabus_json: dict | str | None = None,
    syllabus_slug: str | None = None,
    syllabus_version_number: int | str | None = None,
) -> dict:
    syllabus_json = _load_syllabus_json(
        syllabus_version,
        macro_syllabus_json=macro_syllabus_json,
        syllabus_slug=syllabus_slug,
        syllabus_version_number=syllabus_version_number,
    )
    grading_strategy = syllabus_json.get("grading_strategy") or {}
    completion = grading_strategy.get("completion") or syllabus_json.get("completion")

    if isinstance(completion, dict):
        strategy_type = completion.get("type") or FULL_COMPLETION
        if strategy_type == FULL_COMPLETION:
            return {
                "type": FULL_COMPLETION,
                "source": "syllabus",
                "requirements": {
                    task_type: {"min_percent": 100, "only_mandatory": False} for task_type in TASK_TYPES
                },
            }

        if strategy_type == PARTIAL_COMPLETION:
            requirements = completion.get("requirements") or {}
            normalized_requirements = {}
            for task_type, requirement in requirements.items():
                if task_type not in TASK_TYPES:
                    continue

                requirement = requirement or {}
                normalized_requirements[task_type] = {
                    "min_percent": _normalize_percent(requirement.get("min_percent"), 100),
                    "only_mandatory": bool(requirement.get("only_mandatory", False)),
                }

            return {
                "type": PARTIAL_COMPLETION,
                "source": "syllabus",
                "requirements": normalized_requirements,
            }

    mandatory_projects = get_assets_from_syllabus(
        syllabus_version,
        task_types=["PROJECT"],
        only_mandatory=True,
        macro_syllabus_json=macro_syllabus_json,
        syllabus_slug=syllabus_slug,
        syllabus_version_number=syllabus_version_number,
    )
    if mandatory_projects:
        return {
            "type": LEGACY_PROJECTS,
            "source": "legacy",
            "requirements": {
                "PROJECT": {"min_percent": 100, "only_mandatory": True},
            },
        }

    return {
        "type": NO_COMPLETION_STRATEGY,
        "source": "legacy",
        "requirements": {},
    }


def _requirements_from_strategy(strategy: dict) -> list[CompletionRequirement]:
    requirements: list[CompletionRequirement] = []
    for task_type, requirement in (strategy.get("requirements") or {}).items():
        if task_type not in TASK_TYPES:
            continue

        requirements.append(
            CompletionRequirement(
                task_type=task_type,
                min_percent=_normalize_percent(requirement.get("min_percent"), 100),
                only_mandatory=bool(requirement.get("only_mandatory", False)),
            )
        )

    return requirements


def _is_task_complete(task: Task) -> bool:
    if task.task_type == Task.TaskType.PROJECT:
        return task.revision_status in [Task.RevisionStatus.APPROVED, Task.RevisionStatus.IGNORED]

    if task.task_type == Task.TaskType.EXERCISE:
        return task.revision_status == Task.RevisionStatus.APPROVED or task.task_status == Task.TaskStatus.DONE

    if task.task_type in [Task.TaskType.LESSON, Task.TaskType.QUIZ]:
        return task.task_status == Task.TaskStatus.DONE

    return False


def _evaluate_cohort_user_completion(cohort_user: CohortUser, *, apply_macro_override: bool) -> dict:
    cohort = cohort_user.cohort
    override_kwargs = _override_kwargs_from_cohort_user(cohort_user) if apply_macro_override else None
    override_kwargs = override_kwargs or {}
    strategy = get_completion_strategy(cohort.syllabus_version if cohort else None, **override_kwargs)
    requirements = _requirements_from_strategy(strategy)

    assets_by_requirement: dict[str, set[str]] = {}
    for requirement in requirements:
        assets_by_requirement[requirement.task_type] = get_syllabus_assets_by_type(
            cohort.syllabus_version if cohort else None,
            task_types=[requirement.task_type],
            only_mandatory=requirement.only_mandatory,
            **override_kwargs,
        ).get(requirement.task_type, set())

    all_required_slugs = set()
    for slugs in assets_by_requirement.values():
        all_required_slugs.update(slugs)

    completed_by_type: dict[str, set[str]] = {task_type: set() for task_type in TASK_TYPES}
    if all_required_slugs:
        tasks = Task.objects.filter(
            user=cohort_user.user,
            cohort=cohort,
            associated_slug__in=list(all_required_slugs),
            task_type__in=[requirement.task_type for requirement in requirements],
        )
        for task in tasks:
            if task.associated_slug in assets_by_requirement.get(task.task_type, set()) and _is_task_complete(task):
                completed_by_type.setdefault(task.task_type, set()).add(task.associated_slug)

    required_breakdown = {}
    pending_required_slugs: dict[str, list[str]] = {}
    total_required = 0
    completed_required = 0
    requirements_met = True

    for requirement in requirements:
        slugs = assets_by_requirement.get(requirement.task_type, set())
        completed_slugs = completed_by_type.get(requirement.task_type, set()) & slugs
        total = len(slugs)
        completed = len(completed_slugs)
        percent = round((completed / total) * 100, 2) if total else 0
        is_met = total > 0 and percent >= requirement.min_percent
        missing = sorted(slugs - completed_slugs)

        required_breakdown[requirement.task_type] = {
            "total": total,
            "completed": completed,
            "percent": percent,
            "min_percent": requirement.min_percent,
            "is_met": is_met,
            "only_mandatory": requirement.only_mandatory,
            "missing": missing,
        }
        pending_required_slugs[requirement.task_type] = missing

        total_required += total
        completed_required += completed
        if not is_met:
            requirements_met = False

    if not requirements:
        requirements_met = False

    overall_percent = round((completed_required / total_required) * 100, 2) if total_required else 0

    return {
        "strategy": strategy,
        "is_complete": requirements_met,
        "used_macro_override": bool(apply_macro_override and override_kwargs),
        "overall": {
            "total": total_required,
            "completed": completed_required,
            "percent": overall_percent,
        },
        "required": required_breakdown,
        "pending_required_slugs": pending_required_slugs,
        "pending_required_count": sum(len(slugs) for slugs in pending_required_slugs.values()),
    }


def evaluate_cohort_user_completion(cohort_user: CohortUser) -> dict:
    logger.info(
        "Evaluating completion cohort_user_id=%s user_id=%s cohort_id=%s source_macro_cohort_id=%s",
        cohort_user.id,
        cohort_user.user_id,
        getattr(cohort_user.cohort, "id", None),
        cohort_user.source_macro_cohort_id,
    )
    legacy = _evaluate_cohort_user_completion(cohort_user, apply_macro_override=False)
    if legacy["is_complete"]:
        logger.info(
            "Completion legacy complete=True cohort_user_id=%s pending=%s",
            cohort_user.id,
            legacy["pending_required_count"],
        )
        return legacy

    if _override_kwargs_from_cohort_user(cohort_user) is None:
        logger.info(
            "Completion legacy incomplete and no source_macro override cohort_user_id=%s pending=%s",
            cohort_user.id,
            legacy["pending_required_count"],
        )
        return legacy

    override = _evaluate_cohort_user_completion(cohort_user, apply_macro_override=True)
    logger.info(
        "Completion override pass cohort_user_id=%s complete=%s pending=%s",
        cohort_user.id,
        override["is_complete"],
        override["pending_required_count"],
    )
    return override


def get_completion_cache_key(cohort_user: CohortUser) -> str | None:
    cohort = cohort_user.cohort
    syllabus_version = cohort.syllabus_version if cohort else None
    if cohort_user.id is None or cohort is None or syllabus_version is None:
        return None

    return (
        "admissions:completion:"
        f"cohort_user:{cohort_user.id}:"
        f"user:{cohort_user.user_id}:"
        f"cohort:{cohort.id}:"
        f"source_macro:{cohort_user.source_macro_cohort_id or 0}:"
        f"syllabus_version:{syllabus_version.id}:"
        f"json:{syllabus_version.hashed_json()}"
    )


def cache_cohort_user_completion(cohort_user: CohortUser, completion: dict) -> None:
    cache_key = get_completion_cache_key(cohort_user)
    if cache_key is None or not completion.get("is_complete"):
        return

    cache.set(cache_key, completion, COMPLETION_CACHE_TTL_SECONDS)


def get_cached_cohort_user_completion(cohort_user: CohortUser) -> dict | None:
    cache_key = get_completion_cache_key(cohort_user)
    if cache_key is None:
        return None

    completion = cache.get(cache_key)
    if not isinstance(completion, dict) or not completion.get("is_complete"):
        return None

    return completion


def get_cached_or_evaluate_cohort_user_completion(cohort_user: CohortUser) -> dict:
    completion = get_cached_cohort_user_completion(cohort_user)
    if completion is not None:
        return completion

    return evaluate_cohort_user_completion(cohort_user)


def graduate_cohort_user_if_complete(cohort_user: CohortUser) -> tuple[bool, dict]:
    if cohort_user.educational_status == "GRADUATED":
        return False, get_cached_or_evaluate_cohort_user_completion(cohort_user)

    result = evaluate_cohort_user_completion(cohort_user)
    if not result["is_complete"]:
        return False, result

    cohort_user.educational_status = "GRADUATED"
    cohort_user.save()
    cache_cohort_user_completion(cohort_user, result)
    return True, result

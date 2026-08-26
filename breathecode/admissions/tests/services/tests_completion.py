import pytest
from django.core.cache import cache

from breathecode.admissions.services.completion import (
    evaluate_cohort_user_completion,
    get_cached_cohort_user_completion,
    graduate_cohort_user_if_complete,
)
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def syllabus_json(completion=None):
    data = {
        "days": [
            {
                "lessons": [{"slug": "lesson-1", "mandatory": True}],
                "replits": [{"slug": "exercise-1", "mandatory": True}],
            },
            {
                "quizzes": [{"slug": "quiz-1", "mandatory": True}],
                "assignments": [{"slug": "project-1", "mandatory": True}],
            },
        ],
    }
    if completion:
        data["grading_strategy"] = {"completion": completion}
    return data


@pytest.fixture(autouse=True)
def setup(db, bc: Breathecode):
    def wrapper(completion=None, tasks=None):
        return bc.database.create(
            cohort=1,
            cohort_user=1,
            syllabus_version={"json": syllabus_json(completion)},
            task=tasks or [],
        )

    yield wrapper


def test_legacy_strategy_requires_mandatory_projects(setup):
    model = setup(
        tasks=[
            {
                "associated_slug": "project-1",
                "task_type": "PROJECT",
                "task_status": "DONE",
                "revision_status": "APPROVED",
            }
        ]
    )

    result = evaluate_cohort_user_completion(model.cohort_user)

    assert result["strategy"]["type"] == "LEGACY_PROJECTS"
    assert result["is_complete"] is True
    assert result["required"]["PROJECT"]["percent"] == 100


def test_partial_completion_requires_only_configured_types(setup):
    model = setup(
        completion={
            "type": "PARTIAL_COMPLETION",
            "requirements": {
                "LESSON": {"min_percent": 100},
                "QUIZ": {"min_percent": 100},
            },
        },
        tasks=[
            {"associated_slug": "lesson-1", "task_type": "LESSON", "task_status": "DONE"},
            {"associated_slug": "quiz-1", "task_type": "QUIZ", "task_status": "DONE"},
        ],
    )

    result = evaluate_cohort_user_completion(model.cohort_user)

    assert result["strategy"]["type"] == "PARTIAL_COMPLETION"
    assert result["is_complete"] is True
    assert set(result["required"].keys()) == {"LESSON", "QUIZ"}


def test_full_completion_requires_all_asset_types(setup):
    model = setup(
        completion={"type": "FULL_COMPLETION"},
        tasks=[
            {"associated_slug": "lesson-1", "task_type": "LESSON", "task_status": "DONE"},
            {"associated_slug": "exercise-1", "task_type": "EXERCISE", "task_status": "DONE"},
            {"associated_slug": "quiz-1", "task_type": "QUIZ", "task_status": "DONE"},
        ],
    )

    result = evaluate_cohort_user_completion(model.cohort_user)

    assert result["strategy"]["type"] == "FULL_COMPLETION"
    assert result["is_complete"] is False
    assert result["required"]["PROJECT"]["missing"] == ["project-1"]


def test_no_strategy_and_no_mandatory_projects_does_not_complete(db, bc: Breathecode):
    model = bc.database.create(
        cohort=1,
        cohort_user=1,
        syllabus_version={
            "json": {
                "days": [
                    {
                        "lessons": [{"slug": "lesson-1", "mandatory": True}],
                    }
                ]
            }
        },
        task=[{"associated_slug": "lesson-1", "task_type": "LESSON", "task_status": "DONE"}],
    )

    result = evaluate_cohort_user_completion(model.cohort_user)

    assert result["strategy"]["type"] == "NO_COMPLETION_STRATEGY"
    assert result["is_complete"] is False


def test_graduate_cohort_user_if_complete_caches_completion(setup):
    model = setup(
        tasks=[
            {
                "associated_slug": "project-1",
                "task_type": "PROJECT",
                "task_status": "DONE",
                "revision_status": "APPROVED",
            }
        ]
    )

    graduated, result = graduate_cohort_user_if_complete(model.cohort_user)
    cached = get_cached_cohort_user_completion(model.cohort_user)

    assert graduated is True
    assert result["is_complete"] is True
    assert cached == result


def test_legacy_complete_does_not_need_override(db, bc: Breathecode):
    micro = bc.database.create(
        syllabus={"slug": "micro-course"},
        syllabus_version={
            "version": 1,
            "json": {
                "days": [
                    {
                        "assignments": [
                            {"slug": "project-1", "mandatory": True},
                            {"slug": "project-2", "mandatory": True},
                        ]
                    }
                ]
            },
        },
        cohort=1,
        cohort_user=1,
        task=[
            {
                "associated_slug": "project-1",
                "task_type": "PROJECT",
                "task_status": "DONE",
                "revision_status": "APPROVED",
            },
            {
                "associated_slug": "project-2",
                "task_type": "PROJECT",
                "task_status": "DONE",
                "revision_status": "APPROVED",
            },
        ],
    )
    macro = bc.database.create(
        syllabus={"slug": "macro-course"},
        syllabus_version={"version": 1, "json": {"days": [], "micro-course.v1": {"days": []}}},
        cohort={"micro_cohorts": [micro.cohort]},
    )
    micro.cohort_user.source_macro_cohort = macro.cohort
    micro.cohort_user.save()

    result = evaluate_cohort_user_completion(micro.cohort_user)

    assert result["is_complete"] is True
    assert result["used_macro_override"] is False


def test_override_completes_when_legacy_does_not(db, bc: Breathecode):
    micro = bc.database.create(
        syllabus={"slug": "micro-course"},
        syllabus_version={
            "version": 1,
            "json": {
                "days": [
                    {
                        "assignments": [
                            {"slug": "project-1", "mandatory": True},
                            {"slug": "project-2", "mandatory": True},
                        ]
                    }
                ]
            },
        },
        cohort=1,
        cohort_user=1,
        task=[
            {
                "associated_slug": "project-1",
                "task_type": "PROJECT",
                "task_status": "DONE",
                "revision_status": "APPROVED",
            }
        ],
    )
    macro = bc.database.create(
        syllabus={"slug": "macro-course"},
        syllabus_version={
            "version": 1,
            "json": {
                "days": [],
                "micro-course.v1": {
                    "days": [
                        {
                            "assignments": [
                                {"slug": "project-1", "mandatory": True},
                                {"status": "DELETED"},
                            ]
                        }
                    ]
                },
            },
        },
        cohort={"micro_cohorts": [micro.cohort]},
    )
    micro.cohort_user.source_macro_cohort = macro.cohort
    micro.cohort_user.save()

    result = evaluate_cohort_user_completion(micro.cohort_user)
    graduated, _ = graduate_cohort_user_if_complete(micro.cohort_user)
    micro.cohort_user.refresh_from_db()

    assert result["is_complete"] is True
    assert result["used_macro_override"] is True
    assert result["required"]["PROJECT"]["missing"] == []
    assert graduated is True
    assert micro.cohort_user.educational_status == "GRADUATED"


def test_without_source_macro_stays_legacy_incomplete(db, bc: Breathecode):
    micro = bc.database.create(
        syllabus={"slug": "micro-course"},
        syllabus_version={
            "version": 1,
            "json": {
                "days": [
                    {
                        "assignments": [
                            {"slug": "project-1", "mandatory": True},
                            {"slug": "project-2", "mandatory": True},
                        ]
                    }
                ]
            },
        },
        cohort=1,
        cohort_user=1,
        task=[
            {
                "associated_slug": "project-1",
                "task_type": "PROJECT",
                "task_status": "DONE",
                "revision_status": "APPROVED",
            }
        ],
    )

    result = evaluate_cohort_user_completion(micro.cohort_user)

    assert result["is_complete"] is False
    assert result["used_macro_override"] is False
    assert result["required"]["PROJECT"]["missing"] == ["project-2"]

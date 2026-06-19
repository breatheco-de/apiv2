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

import random

import pytest

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def arange(db, bc: Breathecode, fake):

    def wrapper(task=1, cohort_user=1, syllabus_version={}, cohort=1):
        syll = {
            "json": {
                "days": [
                    {
                        "quizzes": [
                            {
                                "slug": "task-1",
                                "mandatory": True,
                            },
                            {
                                "slug": "task-2",
                                "mandatory": False,
                            },
                        ],
                        "lessons": [
                            {
                                "slug": "task-3",
                                "mandatory": True,
                            },
                            {
                                "slug": "task-4",
                                "mandatory": False,
                            },
                        ],
                    },
                    {
                        "replits": [
                            {
                                "slug": "task-5",
                                "mandatory": True,
                            },
                            {
                                "slug": "task-6",
                                "mandatory": False,
                            },
                        ],
                        "assignments": [
                            {
                                "slug": "task-7",
                                "mandatory": True,
                            },
                            {
                                "slug": "task-8",
                                "mandatory": True,
                            },
                            {
                                "slug": "task-9",
                                "mandatory": False,
                            },
                        ],
                    },
                ],
            },
        }
        return bc.database.create(
            task=task,
            cohort_user=cohort_user,
            cohort=cohort,
            syllabus_version={
                **syll,
                **syllabus_version,
            },
        )

    yield wrapper


def test_no_updating_the_status(enable_signals, bc: Breathecode, arange):
    enable_signals()

    model = arange()

    assert bc.database.list_of("assignments.Task") == [
        bc.format.to_dict(model.task),
    ]

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model.cohort_user),
            "educational_status": "ACTIVE",
        },
    ]


def test_available_as_saas_false(enable_signals, bc: Breathecode, arange):
    enable_signals()

    model = arange(task={"task_status": "PENDING"}, cohort={"available_as_saas": False})

    model.task.task_status = "DONE"
    model.task.save()

    assert bc.database.list_of("assignments.Task") == [
        bc.format.to_dict(model.task),
    ]

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model.cohort_user),
            "educational_status": "ACTIVE",
            "history_log": {
                "delivered_assignments": [
                    {
                        "id": 1,
                        "type": model.task.task_type,
                    }
                ],
                "pending_assignments": [],
            },
        },
    ]


@pytest.mark.parametrize("revision_status1, revision_status2", [("PENDING", "REJECTED"), ("REJECTED", "PENDING")])
def test_available_as_saas_true__no_mandatory_tasks__pending_tasks(
    enable_signals, bc: Breathecode, arange, revision_status1, revision_status2
):
    enable_signals()

    task = {
        "associated_slug": "task-9",
        "task_status": "PENDING",
        "revision_status": revision_status1,
        "task_type": "PROJECT",
    }
    cohort = {"available_as_saas": True}

    model = arange(task=task, cohort=cohort)

    model.task.task_status = "DONE"
    model.task.revision_status = revision_status2
    model.task.save()

    assert bc.database.list_of("assignments.Task") == [
        bc.format.to_dict(model.task),
    ]

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model.cohort_user),
            "educational_status": "ACTIVE",
            "history_log": {
                "delivered_assignments": [
                    {
                        "id": 1,
                        "type": model.task.task_type,
                    }
                ],
                "pending_assignments": [],
            },
        },
    ]


@pytest.mark.parametrize(
    "good_revision_status, bad_revision_status",
    [
        ("IGNORED", "PENDING"),
        ("APPROVED", "REJECTED"),
    ],
)
def test_available_as_saas_true__all_mandatory_tasks_but_one(
    enable_signals, bc: Breathecode, arange, good_revision_status, bad_revision_status
):
    enable_signals()

    tasks = [
        {
            "task_status": "PENDING",
            "associated_slug": f"task-{n}",
            "revision_status": "PENDING",
            "task_type": "PROJECT",
        }
        for n in [1, 3, 5, 7, 8]
    ]

    exception = random.randint(0, 3)
    model = arange(task=tasks, cohort={"available_as_saas": True})

    for n in range(0, 4):
        if n == exception:
            model.task[n].revision_status = bad_revision_status

        else:
            model.task[n].revision_status = good_revision_status

        model.task[n].save()

    for n in range(0, 4):
        if n == exception:
            continue

        model.task[n].task_status = "DONE"
        model.task[n].save()

    assert bc.database.list_of("assignments.Task") == bc.format.to_dict(model.task)

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model.cohort_user),
            "educational_status": "ACTIVE",
            "history_log": {
                "delivered_assignments": [
                    {
                        "id": n + 1,
                        "type": model.task[n].task_type,
                    }
                    for n in range(0, 4)
                    if n != exception
                ],
                "pending_assignments": [],
            },
        },
    ]


@pytest.mark.parametrize("revision_status", ["IGNORED", "APPROVED"])
def test_available_as_saas_true__all_mandatory_tasks(enable_signals, bc: Breathecode, arange, revision_status):
    enable_signals()

    tasks = [
        {
            "task_status": "PENDING",
            "associated_slug": f"task-{n}",
            "revision_status": "PENDING",
            "task_type": "PROJECT",
        }
        for n in [1, 3, 5, 7, 8]
    ]
    cohort = {"available_as_saas": True}

    model = arange(task=tasks, cohort=cohort)

    for n in range(0, 5):
        model.task[n].task_status = "DONE"
        model.task[n].revision_status = revision_status
        model.task[n].save()

    assert bc.database.list_of("assignments.Task") == bc.format.to_dict(model.task)

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model.cohort_user),
            "educational_status": "GRADUATED",
            "history_log": {
                "delivered_assignments": [
                    {
                        "id": n + 1,
                        "type": model.task[n].task_type,
                    }
                    for n in range(0, 5)
                ],
                "pending_assignments": [],
            },
        },
    ]


@pytest.mark.parametrize("task_type", ["QUIZ", "LESSON", "EXERCISE"])
@pytest.mark.parametrize("revision_status1, revision_status2", [("PENDING", "REJECTED"), ("REJECTED", "PENDING")])
def test_available_as_saas_true__all_mandatory_tasks_pending__but_type_is_not_project(
    enable_signals, bc: Breathecode, arange, revision_status1, revision_status2, task_type
):
    enable_signals()

    tasks = [
        {
            "task_status": "PENDING",
            "associated_slug": f"task-{n}",
            "revision_status": revision_status1,
            "task_type": task_type,
        }
        for n in [1, 3, 5, 7, 8]
    ]
    cohort = {"available_as_saas": True}

    model = arange(task=tasks, cohort=cohort)

    for n in range(0, 4):
        model.task[n].task_status = "DONE"
        model.task[n].revision_status = revision_status2
        model.task[n].save()

    assert bc.database.list_of("assignments.Task") == bc.format.to_dict(model.task)

    assert bc.database.list_of("admissions.CohortUser") == [
        {
            **bc.format.to_dict(model.cohort_user),
            "educational_status": "ACTIVE",
            "history_log": {
                "delivered_assignments": [
                    {
                        "id": n + 1,
                        "type": model.task[n].task_type,
                    }
                    for n in range(0, 4)
                ],
                "pending_assignments": [],
            },
        },
    ]

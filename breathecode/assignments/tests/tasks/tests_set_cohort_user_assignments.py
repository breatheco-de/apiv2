"""
Test /answer
"""

import random
from logging import Logger
from unittest.mock import MagicMock, call, patch

import pytest
from linked_services.django.actions import reset_app_cache
from linked_services.django.service import Service

from breathecode.assignments import signals

from ...tasks import set_cohort_user_assignments
from ..mixins import AssignmentsTestCase


@pytest.fixture(autouse=True)
def x(db, monkeypatch):
    empty = lambda *args, **kwargs: None

    reset_app_cache()

    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())

    monkeypatch.setattr("breathecode.assignments.signals.assignment_created.send_robust", empty)
    monkeypatch.setattr("breathecode.assignments.signals.assignment_status_updated.send_robust", empty)
    monkeypatch.setattr("breathecode.activity.tasks.get_attendancy_log.delay", empty)
    monkeypatch.setattr("django.db.models.signals.pre_delete.send_robust", empty)
    monkeypatch.setattr("breathecode.admissions.signals.student_edu_status_updated.send_robust", empty)

    yield


class MediaTestSuite(AssignmentsTestCase):
    """Test /answer"""

    """
    🔽🔽🔽 Without Task
    """

    def test__without_tasks(self):
        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [])
        self.assertEqual(self.bc.database.list_of("admissions.CohortUser"), [])
        self.assertEqual(Logger.info.call_args_list, [call("Executing set_cohort_user_assignments")])
        self.assertEqual(Logger.error.call_args_list, [call("Task not found")])

    """
    🔽🔽🔽 One Task
    """

    def test__with_one_task(self):
        model = self.bc.database.create(task=1, cohort=1)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(self.bc.database.list_of("admissions.CohortUser"), [])
        self.assertEqual(Logger.info.call_args_list, [call("Executing set_cohort_user_assignments")])
        self.assertEqual(Logger.error.call_args_list, [call("CohortUser not found")])

    """
    🔽🔽🔽 One Task
    """

    def test__with_one_task__task_is_pending(self):
        task_type = random.choice(["LESSON", "QUIZ", "PROJECT", "EXERCISE"])
        task = {
            "task_status": "PENDING",
            "task_type": task_type,
        }
        model = self.bc.database.create(task=task, cohort_user=1)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.bc.format.to_dict(model.cohort_user),
                    "history_log": {
                        "delivered_assignments": [],
                        "pending_assignments": [
                            {
                                "id": 1,
                                "type": task_type,
                            },
                        ],
                    },
                },
            ],
        )
        self.assertEqual(
            Logger.info.call_args_list,
            [
                call("Executing set_cohort_user_assignments"),
                call("History log saved"),
            ],
        )
        self.assertEqual(Logger.error.call_args_list, [])

    def test__with_one_task__task_is_done(self):
        task_type = random.choice(["LESSON", "QUIZ", "PROJECT", "EXERCISE"])
        task = {
            "task_status": "DONE",
            "task_type": task_type,
        }
        model = self.bc.database.create(task=task, cohort_user=1)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.bc.format.to_dict(model.cohort_user),
                    "history_log": {
                        "delivered_assignments": [
                            {
                                "id": 1,
                                "type": task_type,
                            },
                        ],
                        "pending_assignments": [],
                    },
                },
            ],
        )
        self.assertEqual(
            Logger.info.call_args_list,
            [
                call("Executing set_cohort_user_assignments"),
                call("History log saved"),
            ],
        )
        self.assertEqual(Logger.error.call_args_list, [])

    """
    🔽🔽🔽 One Task with log
    """

    def test__with_one_task__task_is_pending__with_log__already_exists(self):
        task_type = random.choice(["LESSON", "QUIZ", "PROJECT", "EXERCISE"])
        task = {
            "task_status": "PENDING",
            "task_type": task_type,
        }
        cohort_user = {
            "history_log": {
                "delivered_assignments": [],
                "pending_assignments": [
                    {
                        "id": 1,
                        "type": task_type,
                    },
                ],
            }
        }
        model = self.bc.database.create(task=task, cohort_user=cohort_user)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.bc.format.to_dict(model.cohort_user),
                    "history_log": {
                        "delivered_assignments": [],
                        "pending_assignments": [
                            {
                                "id": 1,
                                "type": task_type,
                            },
                        ],
                    },
                },
            ],
        )
        self.assertEqual(
            Logger.info.call_args_list,
            [
                call("Executing set_cohort_user_assignments"),
                call("History log saved"),
            ],
        )
        self.assertEqual(Logger.error.call_args_list, [])

    def test__with_one_task__task_is_pending__with_log__from_different_items(self):
        task_type = random.choice(["LESSON", "QUIZ", "PROJECT", "EXERCISE"])
        task = {
            "task_status": "PENDING",
            "task_type": task_type,
        }
        cohort_user = {
            "history_log": {
                "delivered_assignments": [
                    {
                        "id": 3,
                        "type": task_type,
                    },
                ],
                "pending_assignments": [
                    {
                        "id": 2,
                        "type": task_type,
                    },
                ],
            }
        }
        model = self.bc.database.create(task=task, cohort_user=cohort_user)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.bc.format.to_dict(model.cohort_user),
                    "history_log": {
                        "delivered_assignments": [
                            {
                                "id": 3,
                                "type": task_type,
                            },
                        ],
                        "pending_assignments": [
                            {
                                "id": 2,
                                "type": task_type,
                            },
                            {
                                "id": 1,
                                "type": task_type,
                            },
                        ],
                    },
                },
            ],
        )
        self.assertEqual(
            Logger.info.call_args_list,
            [
                call("Executing set_cohort_user_assignments"),
                call("History log saved"),
            ],
        )
        self.assertEqual(Logger.error.call_args_list, [])

    def test__rigobot_not_found(self):
        task_type = random.choice(["LESSON", "QUIZ", "PROJECT", "EXERCISE"])
        task = {
            "task_status": "PENDING",
            "task_type": task_type,
            "github_url": self.bc.fake.url(),
        }
        cohort_user = {
            "history_log": {
                "delivered_assignments": [
                    {
                        "id": 3,
                        "type": task_type,
                    },
                ],
                "pending_assignments": [
                    {
                        "id": 2,
                        "type": task_type,
                    },
                ],
            }
        }
        model = self.bc.database.create(task=task, cohort_user=cohort_user, credentials_github=1)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.bc.format.to_dict(model.cohort_user),
                    "history_log": {
                        "delivered_assignments": [
                            {
                                "id": 3,
                                "type": task_type,
                            },
                        ],
                        "pending_assignments": [
                            {
                                "id": 2,
                                "type": task_type,
                            },
                            {
                                "id": 1,
                                "type": task_type,
                            },
                        ],
                    },
                },
            ],
        )
        self.assertEqual(
            Logger.info.call_args_list,
            [
                call("Executing set_cohort_user_assignments"),
                call("History log saved"),
            ],
        )
        self.assertEqual(Logger.error.call_args_list, [call("App rigobot not found")])

    @patch.multiple("linked_services.django.service.Service", post=MagicMock(), put=MagicMock())
    def test__rigobot_cancelled_revision(self):
        task_type = random.choice(["LESSON", "QUIZ", "PROJECT", "EXERCISE"])
        task = {
            "task_status": "PENDING",
            "task_type": task_type,
            "github_url": self.bc.fake.url(),
        }
        cohort_user = {
            "history_log": {
                "delivered_assignments": [
                    {
                        "id": 3,
                        "type": task_type,
                    },
                ],
                "pending_assignments": [
                    {
                        "id": 2,
                        "type": task_type,
                    },
                ],
            }
        }
        model = self.bc.database.create(
            task=task, cohort_user=cohort_user, credentials_github=1, app={"slug": "rigobot"}
        )

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.bc.format.to_dict(model.cohort_user),
                    "history_log": {
                        "delivered_assignments": [
                            {
                                "id": 3,
                                "type": task_type,
                            },
                        ],
                        "pending_assignments": [
                            {
                                "id": 2,
                                "type": task_type,
                            },
                            {
                                "id": 1,
                                "type": task_type,
                            },
                        ],
                    },
                },
            ],
        )
        self.assertEqual(
            Logger.info.call_args_list,
            [
                call("Executing set_cohort_user_assignments"),
                call("History log saved"),
            ],
        )
        self.assertEqual(Logger.error.call_args_list, [])
        self.bc.check.calls(Service.post.call_args_list, [])
        self.bc.check.calls(
            Service.put.call_args_list,
            [call("/v1/finetuning/me/repository/", json={"url": model.task.github_url, "activity_status": "INACTIVE"})],
        )

    @patch.multiple("linked_services.core.service.Service", post=MagicMock(), put=MagicMock())
    def test__rigobot_schedule_revision(self):
        task_type = random.choice(["LESSON", "QUIZ", "PROJECT", "EXERCISE"])
        task = {
            "task_status": "DONE",
            "task_type": task_type,
            "github_url": self.bc.fake.url(),
        }
        cohort_user = {
            "history_log": {
                "delivered_assignments": [
                    {
                        "id": 3,
                        "type": task_type,
                    },
                ],
                "pending_assignments": [
                    {
                        "id": 2,
                        "type": task_type,
                    },
                ],
            }
        }
        model = self.bc.database.create(
            task=task, cohort_user=cohort_user, credentials_github=1, app={"slug": "rigobot"}
        )

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.bc.format.to_dict(model.cohort_user),
                    "history_log": {
                        "delivered_assignments": [
                            {
                                "id": 3,
                                "type": task_type,
                            },
                            {
                                "id": 1,
                                "type": task_type,
                            },
                        ],
                        "pending_assignments": [
                            {
                                "id": 2,
                                "type": task_type,
                            },
                        ],
                    },
                },
            ],
        )
        self.assertEqual(
            Logger.info.call_args_list,
            [
                call("Executing set_cohort_user_assignments"),
                call("History log saved"),
            ],
        )
        self.assertEqual(Logger.error.call_args_list, [])
        self.bc.check.calls(
            Service.post.call_args_list,
            [call("/v1/finetuning/me/repository/", json={"url": model.task.github_url, "watchers": None})],
        )
        self.bc.check.calls(Service.put.call_args_list, [])

    def test__with_one_task__task_is_done__with_log__already_exists(self):
        task_type = random.choice(["LESSON", "QUIZ", "PROJECT", "EXERCISE"])
        task = {
            "task_status": "DONE",
            "task_type": task_type,
        }
        cohort_user = {
            "history_log": {
                "delivered_assignments": [
                    {
                        "id": 1,
                        "type": task_type,
                    },
                ],
                "pending_assignments": [],
            }
        }
        model = self.bc.database.create(task=task, cohort_user=cohort_user)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.bc.format.to_dict(model.cohort_user),
                    "history_log": {
                        "delivered_assignments": [
                            {
                                "id": 1,
                                "type": task_type,
                            },
                        ],
                        "pending_assignments": [],
                    },
                },
            ],
        )
        self.assertEqual(
            Logger.info.call_args_list,
            [
                call("Executing set_cohort_user_assignments"),
                call("History log saved"),
            ],
        )
        self.assertEqual(Logger.error.call_args_list, [])

    def test__with_one_task__task_is_done__with_log__from_different_items(self):
        task_type = random.choice(["LESSON", "QUIZ", "PROJECT", "EXERCISE"])
        task = {
            "task_status": "DONE",
            "task_type": task_type,
        }
        cohort_user = {
            "history_log": {
                "delivered_assignments": [
                    {
                        "id": 3,
                        "type": task_type,
                    },
                ],
                "pending_assignments": [
                    {
                        "id": 2,
                        "type": task_type,
                    },
                ],
            }
        }
        model = self.bc.database.create(task=task, cohort_user=cohort_user)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.bc.format.to_dict(model.cohort_user),
                    "history_log": {
                        "delivered_assignments": [
                            {
                                "id": 3,
                                "type": task_type,
                            },
                            {
                                "id": 1,
                                "type": task_type,
                            },
                        ],
                        "pending_assignments": [
                            {
                                "id": 2,
                                "type": task_type,
                            },
                        ],
                    },
                },
            ],
        )
        self.assertEqual(
            Logger.info.call_args_list,
            [
                call("Executing set_cohort_user_assignments"),
                call("History log saved"),
            ],
        )
        self.assertEqual(Logger.error.call_args_list, [])

"""
Test sync_cohort_user_tasks
"""

from unittest.mock import MagicMock, call, patch


from ...tasks import sync_cohort_user_tasks
from ..mixins import AssignmentsTestCase


def serialize_task(data={}):
    return {
        "id": 1,
        "associated_slug": "intro-to-prework",
        "title": "Introduction to the pre-work",
        "user_id": 1,
        "cohort_id": 1,
        "delivered_at": None,
        "description": "",
        "github_url": None,
        "live_url": None,
        "opened_at": None,
        "revision_status": "PENDING",
        "rigobot_repository_id": None,
        "subtasks": None,
        "task_status": "PENDING",
        "task_type": "LESSON",
        "telemetry_id": None,
        **data,
    }


class MediaTestSuite(AssignmentsTestCase):
    """Test sync_cohort_user_tasks"""

    """
    🔽🔽🔽 Without Cohort User
    """

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test__sync_cohort_user_not_found(self):
        from logging import Logger

        sync_cohort_user_tasks.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [])
        self.assertEqual(Logger.info.call_args_list, [call("Executing sync_cohort_user_tasks for cohort user 1")])
        self.assertEqual(Logger.error.call_args_list, [call("Cohort user not found")])

    @patch("logging.Logger.info", MagicMock())
    def test__sync_cohort_user(self):
        from logging import Logger

        syllabus_json = {
            "days": [
                {
                    "lessons": [
                        {
                            "slug": "megadeth",
                            "title": "Megadeth",
                        }
                    ],
                    "replits": [
                        {
                            "slug": "metallica",
                            "title": "Metallica",
                        }
                    ],
                    "assignments": [
                        {
                            "slug": "anthrax",
                            "title": "Anthrax",
                        }
                    ],
                    "quizzes": [
                        {
                            "slug": "slayer",
                            "title": "Slayer",
                        }
                    ],
                }
            ],
        }
        model_syllabus = self.bc.database.create(syllabus_version={"json": syllabus_json})
        model = self.bc.database.create(cohort={"syllabus_version": model_syllabus["syllabus_version"]}, cohort_user=1)

        # Resetting to avoid logging from the models signals
        Logger.info.call_args_list = []

        sync_cohort_user_tasks.delay(1)

        self.assertEqual(
            self.bc.database.list_of("assignments.Task"),
            [
                serialize_task(data={"associated_slug": "megadeth", "title": "Megadeth"}),
                serialize_task(
                    data={"associated_slug": "metallica", "title": "Metallica", "id": 2, "task_type": "EXERCISE"}
                ),
                serialize_task(
                    data={"associated_slug": "anthrax", "title": "Anthrax", "id": 3, "task_type": "PROJECT"}
                ),
                serialize_task(data={"associated_slug": "slayer", "title": "Slayer", "id": 4, "task_type": "QUIZ"}),
            ],
        )
        self.assertEqual(
            Logger.info.call_args_list,
            [
                call("Executing sync_cohort_user_tasks for cohort user 1"),
                call("Cohort User 1 synced successfully"),
            ],
        )

    @patch("logging.Logger.info", MagicMock())
    def test__sync_cohort_user_with_previous_tasks(self):
        from logging import Logger

        syllabus_json = {
            "days": [
                {
                    "lessons": [
                        {
                            "slug": "megadeth",
                            "title": "Megadeth",
                        }
                    ],
                    "replits": [
                        {
                            "slug": "metallica",
                            "title": "Metallica",
                        }
                    ],
                    "assignments": [
                        {
                            "slug": "anthrax",
                            "title": "Anthrax",
                        }
                    ],
                    "quizzes": [
                        {
                            "slug": "slayer",
                            "title": "Slayer",
                        }
                    ],
                }
            ],
        }
        model_syllabus = self.bc.database.create(syllabus_version={"json": syllabus_json})
        model = self.bc.database.create(
            cohort={"syllabus_version": model_syllabus["syllabus_version"]},
            cohort_user=1,
            task={"associated_slug": "megadeth", "task_type": "LESSON", "title": "Megadeth"},
        )

        # Resetting to avoid logging from the models signals
        Logger.info.call_args_list = []

        sync_cohort_user_tasks.delay(1)

        self.assertEqual(
            self.bc.database.list_of("assignments.Task"),
            [
                self.bc.format.to_dict(model.task),
                serialize_task(
                    data={"associated_slug": "metallica", "title": "Metallica", "id": 2, "task_type": "EXERCISE"}
                ),
                serialize_task(
                    data={"associated_slug": "anthrax", "title": "Anthrax", "id": 3, "task_type": "PROJECT"}
                ),
                serialize_task(data={"associated_slug": "slayer", "title": "Slayer", "id": 4, "task_type": "QUIZ"}),
            ],
        )
        self.assertEqual(
            Logger.info.call_args_list,
            [
                call("Executing sync_cohort_user_tasks for cohort user 1"),
                call("Cohort User 1 synced successfully"),
            ],
        )

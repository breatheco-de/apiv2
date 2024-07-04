"""
Test /academy/cohort
"""

import datetime
import json
import os
from unittest.mock import MagicMock, patch

from mixer.backend.django import mixer

# from random import randint
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_blob_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_client_mock,
)

from ....management.commands.sync_admissions import Command
from ....models import Cohort, CohortUser, User
from ...mixins import AdmissionsTestCase
from ...mocks import LEGACY_API_PATH, apply_screenshotmachine_requests_get_mock

# from ...utils import GenerateModels

HOST = os.environ.get("OLD_BREATHECODE_API")

with open(f"{os.getcwd()}/breathecode/admissions/fixtures/legacy_teachers.json", "r") as file:
    legacy_teachers = json.load(file)

with open(f"{os.getcwd()}/breathecode/admissions/fixtures/legacy_students.json", "r") as file:
    legacy_students = json.load(file)

financial_status = {
    "late": "LATE",
    "fully_paid": "FULLY_PAID",
    "up_to_date": "UP_TO_DATE",
    "uknown": None,
}

educational_status = {
    "under_review": "ACTIVE",
    "currently_active": "ACTIVE",
    "blocked": "SUSPENDED",
    "postponed": "POSTPONED",
    "studies_finished": "GRADUATED",
    "student_dropped": "DROPPED",
}


class AcademyCohortTestSuite(AdmissionsTestCase):
    """Test /academy/cohort"""

    @patch(LEGACY_API_PATH["get"], apply_screenshotmachine_requests_get_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_students(self):
        """Test /academy/cohort without auth"""
        cohorts = set()
        count_cohorts = 0

        for student in legacy_students["data"]:
            for cohort in student["cohorts"]:
                cohorts.add(cohort)
                count_cohorts += 1

        models = [mixer.blend("admissions.Cohort", slug=slug) for slug in cohorts]
        models_dict = [self.remove_dinamics_fields(model.__dict__) for model in models]

        command = Command()
        self.assertEqual(self.count_cohort_user(), 0)

        self.assertEqual(command.students({"override": False}), None)
        self.assertEqual(self.count_cohort(), len(cohorts))
        self.assertEqual(self.count_user(), 10)
        self.assertEqual(self.count_cohort_user(), count_cohorts)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), models_dict)

        cohort_user_acc = 0

        for student in legacy_students["data"]:
            for slug in student["cohorts"]:
                email = student["email"]
                cohort = Cohort.objects.filter(slug=slug).values_list("id", flat=True).first()
                user = User.objects.filter(email=email).values_list("id", flat=True).first()

                filter = {
                    "cohort_id": cohort,
                    "user_id": user,
                }

                self.assertEqual(CohortUser.objects.filter(**filter).count(), 1)

                model = CohortUser.objects.filter(**filter).first().__dict__
                del model["_state"]
                del model["_CohortUser__old_edu_status"]

                self.assertEqual(isinstance(model["created_at"], datetime.datetime), True)
                del model["created_at"]

                self.assertEqual(isinstance(model["updated_at"], datetime.datetime), True)
                del model["updated_at"]

                cohort_user_acc += 1

                self.assertEqual(
                    model,
                    {
                        "id": cohort_user_acc,
                        "cohort_id": cohort,
                        "user_id": user,
                        "educational_status": educational_status[student["status"]],
                        "finantial_status": financial_status[student["financial_status"]],
                        "role": "STUDENT",
                        "watching": False,
                        "history_log": {},
                    },
                )

        self.assertEqual(self.count_cohort_user(), cohort_user_acc)

    @patch(LEGACY_API_PATH["get"], apply_screenshotmachine_requests_get_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_students_twice(self):
        """Test /academy/cohort without auth"""
        cohorts = set()
        count_cohorts = 0

        for student in legacy_students["data"]:
            for cohort in student["cohorts"]:
                cohorts.add(cohort)
                count_cohorts += 1

        models = [mixer.blend("admissions.Cohort", slug=slug) for slug in cohorts]
        models_dict = [self.remove_dinamics_fields(model.__dict__) for model in models]

        command = Command()
        self.assertEqual(self.count_cohort_user(), 0)

        self.assertEqual(command.students({"override": False}), None)
        self.assertEqual(command.students({"override": False}), None)  # call twice
        self.assertEqual(self.count_cohort(), len(cohorts))
        self.assertEqual(self.count_user(), 10)
        self.assertEqual(self.count_cohort_user(), count_cohorts)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), models_dict)

        cohort_user_acc = 0

        for student in legacy_students["data"]:
            for slug in student["cohorts"]:
                email = student["email"]
                cohort = Cohort.objects.filter(slug=slug).values_list("id", flat=True).first()
                user = User.objects.filter(email=email).values_list("id", flat=True).first()

                filter = {
                    "cohort_id": cohort,
                    "user_id": user,
                }

                self.assertEqual(CohortUser.objects.filter(**filter).count(), 1)

                model = CohortUser.objects.filter(**filter).first().__dict__
                del model["_state"]
                del model["_CohortUser__old_edu_status"]

                self.assertEqual(isinstance(model["created_at"], datetime.datetime), True)
                del model["created_at"]

                self.assertEqual(isinstance(model["updated_at"], datetime.datetime), True)
                del model["updated_at"]

                cohort_user_acc += 1

                self.assertEqual(
                    model,
                    {
                        "id": cohort_user_acc,
                        "cohort_id": cohort,
                        "user_id": user,
                        "educational_status": educational_status[student["status"]],
                        "finantial_status": financial_status[student["financial_status"]],
                        "role": "STUDENT",
                        "watching": False,
                        "history_log": {},
                    },
                )

        self.assertEqual(self.count_cohort_user(), cohort_user_acc)

    @patch(LEGACY_API_PATH["get"], apply_screenshotmachine_requests_get_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_teachers(self):
        """Test /academy/cohort without auth"""
        cohorts = set()
        count_cohorts = 0

        for teacher in legacy_teachers["data"]:
            for cohort in teacher["cohorts"]:
                cohorts.add(cohort)
                count_cohorts += 1

        models = [mixer.blend("admissions.Cohort", slug=slug) for slug in cohorts]
        models_dict = [self.remove_dinamics_fields(model.__dict__) for model in models]

        command = Command()
        self.assertEqual(self.count_cohort_user(), 0)

        self.assertEqual(command.teachers({"override": False}), None)
        self.assertEqual(self.count_cohort(), len(cohorts))
        self.assertEqual(self.count_user(), 10)
        self.assertEqual(self.count_cohort_user(), count_cohorts)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), models_dict)

        cohort_user_acc = 0

        for student in legacy_teachers["data"]:
            for slug in student["cohorts"]:
                email = student["username"]
                cohort = Cohort.objects.filter(slug=slug).values_list("id", flat=True).first()
                user = User.objects.filter(email=email).values_list("id", flat=True).first()

                filter = {
                    "cohort_id": cohort,
                    "user_id": user,
                }

                self.assertEqual(CohortUser.objects.filter(**filter).count(), 1)

                model = CohortUser.objects.filter(**filter).first().__dict__
                del model["_state"]
                del model["_CohortUser__old_edu_status"]

                self.assertEqual(isinstance(model["created_at"], datetime.datetime), True)
                del model["created_at"]

                self.assertEqual(isinstance(model["updated_at"], datetime.datetime), True)
                del model["updated_at"]

                cohort_user_acc += 1

                self.assertEqual(
                    model,
                    {
                        "id": cohort_user_acc,
                        "cohort_id": cohort,
                        "user_id": user,
                        "educational_status": "ACTIVE",
                        "finantial_status": None,
                        "role": "TEACHER",
                        "watching": False,
                        "history_log": {},
                    },
                )

        self.assertEqual(self.count_cohort_user(), cohort_user_acc)

    @patch(LEGACY_API_PATH["get"], apply_screenshotmachine_requests_get_mock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_teachers_twice(self):
        """Test /academy/cohort without auth"""
        cohorts = set()
        count_cohorts = 0

        for teacher in legacy_teachers["data"]:
            for cohort in teacher["cohorts"]:
                cohorts.add(cohort)
                count_cohorts += 1

        models = [mixer.blend("admissions.Cohort", slug=slug) for slug in cohorts]
        models_dict = [self.remove_dinamics_fields(model.__dict__) for model in models]

        command = Command()
        self.assertEqual(self.count_cohort_user(), 0)

        self.assertEqual(command.teachers({"override": False}), None)
        self.assertEqual(command.teachers({"override": False}), None)  # call twice
        self.assertEqual(self.count_cohort(), len(cohorts))
        self.assertEqual(self.count_user(), 10)
        self.assertEqual(self.count_cohort_user(), count_cohorts)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), models_dict)

        cohort_user_acc = 0

        for student in legacy_teachers["data"]:
            for slug in student["cohorts"]:
                email = student["username"]
                cohort = Cohort.objects.filter(slug=slug).values_list("id", flat=True).first()
                user = User.objects.filter(email=email).values_list("id", flat=True).first()

                filter = {
                    "cohort_id": cohort,
                    "user_id": user,
                }

                self.assertEqual(CohortUser.objects.filter(**filter).count(), 1)

                model = CohortUser.objects.filter(**filter).first().__dict__
                del model["_state"]
                del model["_CohortUser__old_edu_status"]

                self.assertEqual(isinstance(model["created_at"], datetime.datetime), True)
                del model["created_at"]

                self.assertEqual(isinstance(model["updated_at"], datetime.datetime), True)
                del model["updated_at"]

                cohort_user_acc += 1

                self.assertEqual(
                    model,
                    {
                        "id": cohort_user_acc,
                        "cohort_id": cohort,
                        "user_id": user,
                        "educational_status": "ACTIVE",
                        "finantial_status": None,
                        "role": "TEACHER",
                        "watching": False,
                        "history_log": {},
                    },
                )

        self.assertEqual(self.count_cohort_user(), cohort_user_acc)

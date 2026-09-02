"""
Test /cohort/:id/user/:id
"""

import re
from unittest.mock import MagicMock, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.admissions.models import CohortUser
from breathecode.admissions.services.completion import evaluate_cohort_user_completion
from ..mixins import AdmissionsTestCase

UTC_NOW = timezone.now()


def _source_macro_payload(cohort_user):
    if cohort_user is None or cohort_user.source_macro_cohort is None:
        return None
    cohort = cohort_user.source_macro_cohort
    return {"id": cohort.id, "slug": cohort.slug, "name": cohort.name}


def _completion_payload(cohort_user):
    if cohort_user is None:
        return None
    return evaluate_cohort_user_completion(cohort_user)


def post_serializer(self, cohort, user, profile_academy=None, data={}):
    cohort_user = CohortUser.objects.filter(id=data.get("id", 1)).first()
    return {
        "cohort": {
            "ending_date": cohort.ending_date,
            "id": cohort.id,
            "kickoff_date": (
                self.bc.datetime.to_iso_string(cohort.kickoff_date) if cohort.kickoff_date else cohort.kickoff_date
            ),
            "name": cohort.name,
            "slug": cohort.slug,
            "stage": cohort.stage,
            "available_as_saas": cohort.available_as_saas,
            "shortcuts": cohort.shortcuts,
            "micro_cohorts": list(cohort.micro_cohorts.values_list("id", flat=True)),
            "syllabus_version": None,
        },
        "created_at": self.bc.datetime.to_iso_string(UTC_NOW),
        "updated_at": self.bc.datetime.to_iso_string(UTC_NOW),
        "educational_status": "ACTIVE",
        "finantial_status": "UP_TO_DATE",
        "id": 1,
        "profile_academy": (
            {
                "email": profile_academy.email,
                "first_name": profile_academy.first_name,
                "id": profile_academy.id,
                "last_name": profile_academy.last_name,
                "phone": profile_academy.phone,
            }
            if profile_academy
            else None
        ),
        "role": "STUDENT",
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
            "last_login": user.last_login,
        },
        "watching": False,
        "source_macro_cohort": _source_macro_payload(cohort_user),
        "completion": _completion_payload(cohort_user),
        **data,
    }


def cohort_user_field(data={}):
    return {
        "cohort_id": 0,
        "educational_status": "ACTIVE",
        "finantial_status": "UP_TO_DATE",
        "id": 0,
        "role": "STUDENT",
        "user_id": 0,
        "watching": False,
        "history_log": {},
        "source_macro_cohort_id": None,
        **data,
    }


def put_serializer(self, cohort_user, cohort, user, profile_academy=None, data={}):
    return {
        "cohort": {
            "ending_date": cohort.ending_date,
            "id": cohort.id,
            "kickoff_date": (
                self.bc.datetime.to_iso_string(cohort.kickoff_date) if cohort.kickoff_date else cohort.kickoff_date
            ),
            "name": cohort.name,
            "slug": cohort.slug,
            "stage": cohort.stage,
            "available_as_saas": cohort.available_as_saas,
            "shortcuts": cohort.shortcuts,
            "micro_cohorts": list(cohort.micro_cohorts.values_list("id", flat=True)),
            "syllabus_version": None,
        },
        "created_at": self.bc.datetime.to_iso_string(cohort_user.created_at),
        "updated_at": self.bc.datetime.to_iso_string(cohort_user.updated_at),
        "educational_status": cohort_user.educational_status,
        "finantial_status": cohort_user.finantial_status,
        "id": cohort_user.id,
        "profile_academy": (
            {
                "email": profile_academy.email,
                "first_name": profile_academy.first_name,
                "id": profile_academy.id,
                "last_name": profile_academy.last_name,
                "phone": profile_academy.phone,
            }
            if profile_academy
            else None
        ),
        "role": cohort_user.role,
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "id": user.id,
            "last_name": user.last_name,
            "last_login": user.last_login,
        },
        "watching": cohort_user.watching,
        "source_macro_cohort": _source_macro_payload(cohort_user),
        "completion": _completion_payload(cohort_user),
        **data,
    }


def check_cohort_user_that_not_have_role_student_can_be_teacher(self, role, update=False, additional_data={}):
    """Test /cohort/:id/user without auth"""
    self.headers(academy=1)

    model_kwargs = {
        "authenticate": True,
        "cohort": True,
        "user": True,
        "profile_academy": True,
        "role": role,
        "capability": "crud_cohort",
    }

    if update:
        model_kwargs["cohort_user"] = True

    model = self.generate_models(**model_kwargs)

    url = reverse_lazy("admissions:cohort_id_user", kwargs={"cohort_id": 1})
    data = {"user": model["user"].id, "role": "TEACHER"}

    request_func = self.client.put if update else self.client.post
    response = request_func(url, data, format="json")

    json = response.json()
    expected = post_serializer(
        self,
        model.cohort,
        model.user,
        model.profile_academy,
        data={
            "role": "TEACHER",
            **additional_data,
        },
    )

    expected["educational_status"] = "ACTIVE"
    expected["finantial_status"] = None if update else "UP_TO_DATE"

    self.assertEqual(json, expected)

    if update:
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    else:
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    if update:
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.model_to_dict(model, "cohort_user"),
                    "role": "TEACHER",
                }
            ],
        )
    else:
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    "cohort_id": 1,
                    "educational_status": "ACTIVE",
                    "finantial_status": "UP_TO_DATE",
                    "id": 1,
                    "role": "TEACHER",
                    "user_id": 1,
                    "watching": False,
                    "source_macro_cohort_id": None,
                }
            ],
        )


class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""

    """
    🔽🔽🔽 Auth
    """

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_user__without_auth(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_id_user_id", kwargs={"cohort_id": 1, "user_id": 1})
        response = self.client.post(url, {})
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 Post method
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_user__post(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            cohort={"stage": "STARTED"},
            user=True,
            profile_academy=True,
            capability="crud_cohort",
            role="potato",
        )

        url = reverse_lazy("admissions:academy_cohort_id_user_id", kwargs={"cohort_id": 1, "user_id": 1})
        data = {
            "user": model["user"].id,
            "cohort": model["cohort"].id,
        }
        response = self.client.post(url, data, format="json")
        json = response.json()
        expected = post_serializer(
            self,
            model.cohort,
            model.user,
            model.profile_academy,
            data={
                "id": 1,
                "role": "STUDENT",
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    "cohort_id": 1,
                    "educational_status": "ACTIVE",
                    "finantial_status": "UP_TO_DATE",
                    "id": 1,
                    "role": "STUDENT",
                    "user_id": 1,
                    "watching": False,
                    "history_log": {},
                    "source_macro_cohort_id": None,
                }
            ],
        )

    """
    🔽🔽🔽 Add the same teacher to two cohors
    """

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_user__post__same_teacher_in_two_cohorts(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        models = [
            self.generate_models(
                authenticate=True,
                user=True,
                cohort={"stage": "STARTED"},
                profile_academy=True,
                capability="crud_cohort",
                role="staff",
            )
        ]

        base = models[0].copy()
        del base["cohort"]

        models = models + [self.generate_models(cohort={"stage": "STARTED"}, models=base)]
        url = reverse_lazy("admissions:academy_cohort_id_user_id", kwargs={"cohort_id": 1, "user_id": 1})
        data = {
            "user": 1,
            "cohort": 1,
            "role": "TEACHER",
        }
        response = self.client.post(url, data, format="json")

        data = {
            "user": 1,
            "cohort": 2,
            "role": "TEACHER",
        }
        url = reverse_lazy("admissions:academy_cohort_id_user_id", kwargs={"cohort_id": 2, "user_id": 1})
        response = self.client.post(url, data, format="json")
        json = response.json()
        model = models[1]
        expected = post_serializer(
            self,
            model.cohort,
            model.user,
            model.profile_academy,
            data={
                "id": 2,
                "role": "TEACHER",
            },
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    "cohort_id": 1,
                    "educational_status": "ACTIVE",
                    "finantial_status": "UP_TO_DATE",
                    "id": 1,
                    "role": "TEACHER",
                    "user_id": 1,
                    "watching": False,
                    "history_log": {},
                    "source_macro_cohort_id": None,
                },
                {
                    "cohort_id": 2,
                    "educational_status": "ACTIVE",
                    "finantial_status": "UP_TO_DATE",
                    "id": 2,
                    "role": "TEACHER",
                    "user_id": 1,
                    "watching": False,
                    "history_log": {},
                    "source_macro_cohort_id": None,
                },
            ],
        )

    """
    🔽🔽🔽 Put
    """

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_user__put(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_id_user_id", kwargs={"cohort_id": 1, "user_id": 1})
        model = self.generate_models(
            authenticate=True, cohort_user=True, profile_academy=True, capability="crud_cohort", role="potato"
        )
        data = {
            "id": model["cohort_user"].id,
            "user": 1,
            "cohort": 1,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()

        # Refresh the model to get the updated_at value after the PUT operation
        model["cohort_user"].refresh_from_db()

        expected = put_serializer(
            self, model.cohort_user, model.cohort, model.user, model.profile_academy, data={"role": "STUDENT"}
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.model_to_dict(model, "cohort_user"),
                    "role": "STUDENT",
                    "watching": False,
                    "source_macro_cohort_id": None,
                }
            ],
        )

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_user__put__graduated_with_pending_tasks(self):
        """Academy staff can mark GRADUATED even if required projects are still pending."""
        self.headers(academy=1)
        task = {"task_status": "PENDING", "task_type": "PROJECT", "associated_slug": "testing-slug"}
        model = self.generate_models(
            authenticate=True,
            cohort_user=True,
            profile_academy=True,
            capability="crud_cohort",
            role="potato",
            task=task,
            syllabus_version={
                "id": 1,
                "json": {
                    "days": [
                        {
                            "assignments": [
                                {
                                    "slug": "testing-slug",
                                }
                            ]
                        }
                    ]
                },
            },
        )
        url = reverse_lazy("admissions:academy_cohort_id_user_id", kwargs={"cohort_id": 1, "user_id": 1})
        data = {
            "educational_status": "GRADUATED",
        }
        response = self.client.put(url, data, format="json")
        json = response.json()

        model["cohort_user"].refresh_from_db()
        model["cohort"].refresh_from_db()

        syllabus_version = model.cohort.syllabus_version
        expected = put_serializer(
            self,
            model.cohort_user,
            model.cohort,
            model.user,
            model.profile_academy,
            data={"educational_status": "GRADUATED"},
        )
        expected["cohort"]["syllabus_version"] = {
            "id": syllabus_version.id,
            "version": syllabus_version.version,
            "slug": syllabus_version.syllabus.slug if syllabus_version.syllabus else None,
            "name": syllabus_version.syllabus.name if syllabus_version.syllabus else None,
            "syllabus": syllabus_version.syllabus.id if syllabus_version.syllabus else None,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.model_to_dict(model, "cohort_user"),
                    "educational_status": "GRADUATED",
                    "watching": False,
                    "source_macro_cohort_id": None,
                }
            ],
        )

    """
    🔽🔽🔽 Put teacher
    """

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_user__put__teacher_with_role_student(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_id_user_id", kwargs={"cohort_id": 1, "user_id": 1})
        model = self.generate_models(
            authenticate=True, cohort_user=True, profile_academy=True, capability="crud_cohort", role="student"
        )
        data = {
            "id": model["cohort_user"].id,
            "role": "TEACHER",
            "user": 1,
            "cohort": 1,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {
            "detail": "The user must be staff member to this academy before it can be a teacher",
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.model_to_dict(model, "cohort_user"),
                    "role": "STUDENT",
                }
            ],
        )

    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_user__put__teacher(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_cohort_id_user_id", kwargs={"cohort_id": 1, "user_id": 1})
        model = self.generate_models(
            authenticate=True, cohort_user=True, profile_academy=True, capability="crud_cohort", role="staff"
        )
        data = {
            "id": model["cohort_user"].id,
            "role": "TEACHER",
            "user": 1,
            "cohort": 1,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()

        # Refresh the model to get the updated_at value after the PUT operation
        model["cohort_user"].refresh_from_db()

        expected = put_serializer(
            self, model.cohort_user, model.cohort, model.user, model.profile_academy, data={"role": "TEACHER"}
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("admissions.CohortUser"),
            [
                {
                    **self.model_to_dict(model, "cohort_user"),
                    "role": "TEACHER",
                    "watching": False,
                    "source_macro_cohort_id": None,
                }
            ],
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_staff(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "staff", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_teacher(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "teacher", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_syllabus_coordinator(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "syllabus_coordinator", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_homework_reviewer(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "homework_reviewer", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_growth_manager(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "growth_manager", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_culture_and_recruitment(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "culture_and_recruitment", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_country_manager(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "country_manager", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_community_manager(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "community_manager", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_career_support(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "career_support", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_assistant(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "assistant", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_admissions_developer(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "admissions_developer", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_admin(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "admin", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_academy_token(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "academy_token", update=True, additional_data={"watching": False}
        )

    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_academy_cohort_id_user__post__one_teacher__with_role_academy_coordinator(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, "academy_coordinator", update=True, additional_data={"watching": False}
        )

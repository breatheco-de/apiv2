"""
Tasks tests
"""

import hashlib
from unittest.mock import MagicMock, call, patch

import pytest
from django.utils import timezone

import breathecode.certificate.signals as signals
from breathecode.tests.mixins.legacy import LegacyAPITestCase
from capyc.rest_framework.exceptions import ValidationException

from ...actions import generate_certificate, strings
from ..mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_blob_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_client_mock,
)


class TestActionGenerateCertificate(LegacyAPITestCase):
    # TODO: this function fix the difference between run tests in all modules
    # and certificate, should be removed in a future
    def clear_preview_url(self, dicts: list[dict]):
        """
        Clear preview url to evit one diff when run test in all tests and just
        certificate tests
        """
        return [{**item, "preview_url": None} for item in dicts]

    def clear_keys(self, dicts, keys):
        _d = {}
        for k in keys:
            _d[k] = None

        return [{**item, **_d} for item in dicts]

    def remove_is_clean_for_one_item(self, item):
        if "is_cleaned" in item:
            del item["is_cleaned"]
        return item

    def generate_update_hash(self, instance):
        kwargs = {
            "signed_by": instance.signed_by,
            "signed_by_role": instance.signed_by_role,
            "status": instance.status,
            "layout": instance.layout,
            "expires_at": instance.expires_at,
            "issued_at": instance.issued_at,
        }

        important_fields = ["signed_by", "signed_by_role", "status", "layout", "expires_at", "issued_at"]

        important_values = "-".join(
            [str(kwargs.get(field) if field in kwargs else None) for field in sorted(important_fields)]
        )

        return hashlib.sha1(important_values.encode("UTF-8")).hexdigest()

    """
    🔽🔽🔽 With User and without Cohort
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__with_user_without_cohort(self):
        model = self.generate_models(user=True)
        try:
            generate_certificate(model["user"])
            assert False
        except Exception as e:
            self.assertEqual(str(e), "missing-cohort-user")

        self.assertEqual(self.bc.database.list_of("certificate.UserSpecialty"), [])

        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 without CohortUser
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__without_cohort_user(self):
        model = self.generate_models(user=True, cohort=True)
        try:
            generate_certificate(model["user"], model["cohort"])
            assert False
        except Exception as e:
            self.assertEqual(str(e), "missing-cohort-user")

        self.assertEqual(self.bc.database.list_of("certificate.UserSpecialty"), [])

        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Cohort not ended
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__cohort_not_ended(self):
        cohort_user_kwargs = {
            "finantial_status": "FULLY_PAID",
            "educational_status": "GRADUATED",
        }
        cohort_kwargs = {
            "current_day": 43877965,
        }
        syllabus_kwargs = {
            "duration_in_days": 43877965,
        }
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus=True,
            syllabus_version=True,
            specialty=True,
            syllabus_schedule=True,
            layout_design=True,
            cohort_user_kwargs=cohort_user_kwargs,
            cohort_kwargs=cohort_kwargs,
            syllabus_kwargs=syllabus_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )

        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

        translation = strings[model["cohort"].language]
        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": (teacher_model["user"].first_name + " " + teacher_model["user"].last_name),
            "signed_by_role": translation["Main Instructor"],
            "specialty_id": 1,
            "issued_at": None,
            "status": "ERROR",
            "token": None,
            "status_text": "cohort-without-status-ended",
            "user_id": 1,
            "update_hash": self.generate_update_hash(user_specialty),
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.bc.database.list_of("certificate.UserSpecialty"), ["preview_url", "token"]), [expected]
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    """
    🔽🔽🔽 without SyllabusVersion
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__without_syllabus_version(self):
        cohort_kwargs = {"stage": "ENDED"}
        model = self.generate_models(user=True, cohort=True, cohort_user=True, cohort_kwargs=cohort_kwargs)
        try:
            generate_certificate(model["user"], model["cohort"])
            assert False
        except Exception as e:
            self.assertEqual(str(e), "missing-syllabus-version")

        self.assertEqual(self.bc.database.list_of("certificate.UserSpecialty"), [])

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 without Specialty
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__without_specialty(self):
        cohort_kwargs = {"stage": "ENDED"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_schedule=True,
            syllabus_version=True,
            cohort_kwargs=cohort_kwargs,
        )
        try:
            generate_certificate(model["user"], model["cohort"])
            assert False
        except Exception as e:
            self.assertEqual(str(e), "missing-specialty")

        self.assertEqual(self.bc.database.list_of("certificate.UserSpecialty"), [])

        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 without Syllabus
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__without_syllabus(self):
        cohort_kwargs = {"stage": "ENDED"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus_schedule=True,
            cohort_kwargs=cohort_kwargs,
        )
        try:
            generate_certificate(model["user"], model["cohort"])
            assert False
        except Exception as e:
            self.assertEqual(str(e), "missing-specialty")

        self.assertEqual(self.bc.database.list_of("certificate.UserSpecialty"), [])

        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 without default Layout
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__without_specialty_layout(self):
        cohort_kwargs = {"stage": "ENDED"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            cohort_kwargs=cohort_kwargs,
        )
        try:
            generate_certificate(model["user"], model["cohort"])
            assert False
        except Exception as e:
            self.assertEqual(str(e), "no-default-layout")

        self.assertEqual(self.bc.database.list_of("certificate.UserSpecialty"), [])

        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 without main teacher
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__without_teacher(self):
        cohort_kwargs = {"stage": "ENDED"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
        )
        try:
            generate_certificate(model["user"], model["cohort"])
            assert False
        except Exception as e:
            self.assertEqual(str(e), "without-main-teacher")

        self.assertEqual(self.bc.database.list_of("certificate.UserSpecialty"), [])

        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Bad financial status
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate_with_bad_student_financial_status(self):
        cohort_kwargs = {"stage": "ENDED"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )
        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

        translation = strings[model["cohort"].language]
        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": (teacher_model["user"].first_name + " " + teacher_model["user"].last_name),
            "signed_by_role": translation["Main Instructor"],
            "specialty_id": 1,
            "issued_at": None,
            "status": "ERROR",
            "token": None,
            "status_text": "bad-finantial-status",
            "user_id": 1,
            "update_hash": self.generate_update_hash(user_specialty),
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.bc.database.list_of("certificate.UserSpecialty"), ["preview_url", "token"]), [expected]
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    """
    🔽🔽🔽 Student with pending tasks
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__with_student_that_didnt_finish_tasks(self):
        cohort_kwargs = {"stage": "ENDED"}
        task_kwargs = {"task_type": "PROJECT", "revision_status": "PENDING"}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE"}
        model = self.generate_models(
            user=2,
            cohort=True,
            cohort_user=True,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
            syllabus_version={
                "id": 1,
                "json": {"days": [{"assignments": [{"slug": "testing-slug", "mandatory": True}]}]},
            },
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
        )

        task_model = self.generate_models(
            task=[
                {"user": model["user"][0], "associated_slug": "testing-slug"},
                {"user": model["user"][1], "associated_slug": "testing-slug"},
            ],
            task_kwargs=task_kwargs,
            models=model,
        )

        base = task_model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )
        result = self.remove_dinamics_fields(generate_certificate(model["user"][0], model["cohort"]).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": strings[model["cohort"].language]["Main Instructor"],
            "specialty_id": 1,
            "issued_at": None,
            "status": "ERROR",
            "token": None,
            "status_text": "with-pending-tasks-1",
            "user_id": 1,
            "update_hash": self.generate_update_hash(user_specialty),
        }
        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.bc.database.list_of("certificate.UserSpecialty"), ["preview_url", "token"]), [expected]
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    """
    🔽🔽🔽 Student with pending tasks without mandatory property
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__with_student_that_didnt_finish_tasks_without_mandatory(self):
        cohort_kwargs = {"stage": "ENDED"}
        task_kwargs = {"task_type": "PROJECT", "revision_status": "PENDING"}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version={"id": 1, "json": {"days": [{"assignments": [{"slug": "testing-slug"}]}]}},
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            task={"associated_slug": "testing-slug"},
            task_kwargs=task_kwargs,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )
        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": strings[model["cohort"].language]["Main Instructor"],
            "specialty_id": 1,
            "issued_at": None,
            "status": "ERROR",
            "token": None,
            "status_text": "with-pending-tasks-1",
            "user_id": 1,
            "update_hash": self.generate_update_hash(user_specialty),
        }
        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.bc.database.list_of("certificate.UserSpecialty"), ["preview_url", "token"]), [expected]
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    """
    🔽🔽🔽 Student with non mandatory pending tasks without
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__with_student_that_didnt_finish_mandatory_tasks(self):
        cohort_kwargs = {"stage": "ENDED"}
        task_kwargs = {"task_type": "PROJECT", "revision_status": "PENDING"}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version={
                "id": 1,
                "json": {"days": [{"assignments": [{"slug": "testing-slug", "mandatory": False}]}]},
            },
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            task={"associated_slug": "testing-slug"},
            task_kwargs=task_kwargs,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )
        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": strings[model["cohort"].language]["Main Instructor"],
            "specialty_id": 1,
            "issued_at": None,
            "status": "ERROR",
            "token": None,
            "status_text": "bad-educational-status",
            "user_id": 1,
            "update_hash": self.generate_update_hash(user_specialty),
        }
        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.bc.database.list_of("certificate.UserSpecialty"), ["preview_url", "token"]), [expected]
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    """
    🔽🔽🔽 Student not graduated
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__without_proper_educational_status(self):
        cohort_kwargs = {"stage": "ENDED"}
        cohort_user_kwargs = {"finantial_status": "FULLY_PAID"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )
        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": strings[model["cohort"].language]["Main Instructor"],
            "specialty_id": 1,
            "issued_at": None,
            "status": "ERROR",
            "status_text": "bad-educational-status",
            "token": None,
            "user_id": 1,
            "update_hash": self.generate_update_hash(user_specialty),
        }
        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.bc.database.list_of("certificate.UserSpecialty"), ["preview_url", "token"]), [expected]
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    """
    🔽🔽🔽 Student with bad finantial_status
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__with_cohort_user__with_finantial_status_eq_up_to_date(self):
        cohort_kwargs = {"stage": "ENDED"}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )
        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)
        self.assertToken(result["token"])
        result["token"] = None

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": strings[model["cohort"].language]["Main Instructor"],
            "specialty_id": 1,
            "issued_at": None,
            "status": "ERROR",
            "status_text": "bad-educational-status",
            "token": None,
            "user_id": 1,
            "update_hash": self.generate_update_hash(user_specialty),
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.bc.database.list_of("certificate.UserSpecialty"), ["preview_url", "token"]), [expected]
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    """
    🔽🔽🔽 Student dropped
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__with_cohort_user__with_educational_status_eq_dropped(self):
        cohort_kwargs = {"stage": "ENDED"}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE", "educational_status": "DROPPED"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )
        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)

        self.assertToken(result["token"])
        result["token"] = None

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": strings[model["cohort"].language]["Main Instructor"],
            "specialty_id": 1,
            "issued_at": None,
            "status": "ERROR",
            "status_text": "bad-educational-status",
            "token": None,
            "user_id": 1,
            "update_hash": self.generate_update_hash(user_specialty),
        }

        self.assertEqual(result, expected)
        self.assertEqual(
            self.clear_keys(self.bc.database.list_of("certificate.UserSpecialty"), ["preview_url", "token"]), [expected]
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    """
    🔽🔽🔽 Cohort not finished
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__with_cohort_not_finished(self):
        cohort_kwargs = {"stage": "ENDED"}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE", "educational_status": "GRADUATED"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )
        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)
        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": strings[model["cohort"].language]["Main Instructor"],
            "specialty_id": 1,
            "issued_at": None,
            "status": "ERROR",
            "status_text": "cohort-not-finished",
            "user_id": 1,
            "update_hash": self.generate_update_hash(user_specialty),
        }

        self.assertToken(result["token"])
        token = result["token"]
        del result["token"]

        self.assertEqual(result, expected)

        self.assertEqual(
            self.clear_preview_url(self.bc.database.list_of("certificate.UserSpecialty")),
            [
                {
                    **expected,
                    "token": token,
                }
            ],
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    """
    🔽🔽🔽 Generate certificate
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate(self):
        cohort_kwargs = {"stage": "ENDED", "current_day": 9545799}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE", "educational_status": "GRADUATED"}
        syllabus_kwargs = {"duration_in_days": 9545799}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
            syllabus_kwargs=syllabus_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )

        start = timezone.now()
        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)
        end = timezone.now()
        issued_at = result["issued_at"]
        self.assertGreater(issued_at, start)
        self.assertLess(issued_at, end)
        del result["issued_at"]
        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": strings[model["cohort"].language]["Main Instructor"],
            "specialty_id": 1,
            "status": "PERSISTED",
            "status_text": "Certificate successfully queued for PDF generation",
            "user_id": 1,
            "is_cleaned": True,
            "update_hash": self.generate_update_hash(user_specialty),
        }

        self.assertToken(result["token"])
        token = result["token"]
        del result["token"]

        self.assertEqual(result, expected)
        del expected["is_cleaned"]

        self.assertEqual(
            self.clear_preview_url(self.bc.database.list_of("certificate.UserSpecialty")),
            [{**expected, "token": token, "issued_at": issued_at}],
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    """
    🔽🔽🔽 Translations
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__lang_en(self):
        cohort_kwargs = {"stage": "ENDED", "current_day": 9545799, "language": "en"}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE", "educational_status": "GRADUATED"}
        syllabus_kwargs = {"duration_in_days": 9545799}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
            syllabus_kwargs=syllabus_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )

        start = timezone.now()
        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)
        end = timezone.now()
        issued_at = result["issued_at"]
        self.assertGreater(issued_at, start)
        self.assertLess(issued_at, end)

        del result["issued_at"]

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": strings[model["cohort"].language]["Main Instructor"],
            "specialty_id": 1,
            "status": "PERSISTED",
            "status_text": "Certificate successfully queued for PDF generation",
            "user_id": 1,
            "is_cleaned": True,
            "update_hash": self.generate_update_hash(user_specialty),
        }

        self.assertToken(result["token"])
        token = result["token"]
        del result["token"]

        self.assertEqual(result, expected)
        del expected["is_cleaned"]

        self.assertEqual(
            self.clear_preview_url(self.bc.database.list_of("certificate.UserSpecialty")),
            [{**expected, "token": token, "issued_at": issued_at}],
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @pytest.mark.parametrize(
        "current_day,duration_in_days,never_ends",
        [
            (9545799, 9545799, False),
            (1, 9545799, True),
        ],
    )
    def test_generate_certificate__lang_es(self, current_day, duration_in_days, never_ends):
        cohort_kwargs = {"stage": "ENDED", "current_day": current_day, "language": "es", "never_ends": never_ends}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE", "educational_status": "GRADUATED"}
        syllabus_kwargs = {"duration_in_days": duration_in_days}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
            syllabus_kwargs=syllabus_kwargs,
        )

        signals.user_specialty_saved.send_robust.call_args_list = []

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )
        start = timezone.now()
        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)
        end = timezone.now()
        issued_at = result["issued_at"]
        self.assertGreater(issued_at, start)
        self.assertLess(issued_at, end)
        del result["issued_at"]

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": strings[model["cohort"].language]["Main Instructor"],
            "specialty_id": 1,
            "status": "PERSISTED",
            "status_text": "Certificate successfully queued for PDF generation",
            "user_id": 1,
            "is_cleaned": True,
            "update_hash": self.generate_update_hash(user_specialty),
        }

        self.assertToken(result["token"])
        token = result["token"]
        del result["token"]

        self.assertEqual(result, expected)
        del expected["is_cleaned"]

        self.assertEqual(
            self.clear_preview_url(self.bc.database.list_of("certificate.UserSpecialty")),
            [{**expected, "token": token, "issued_at": issued_at}],
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    @pytest.mark.parametrize("stage", ["INACTIVE", "PREWORK", "STARTED", "FINAL_PROJECT", "ENDED"])
    def test_generate_certificate__lang_es__never_ends_true(self, stage):
        cohort_kwargs = {"stage": stage, "current_day": 1, "language": "es", "never_ends": True}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE", "educational_status": "GRADUATED"}
        syllabus_kwargs = {"duration_in_days": 9545799}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
            syllabus_kwargs=syllabus_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )

        signals.user_specialty_saved.send_robust.call_args_list = []

        start = timezone.now()
        result = self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)
        end = timezone.now()
        issued_at = result["issued_at"]
        self.assertGreater(issued_at, start)
        self.assertLess(issued_at, end)
        del result["issued_at"]

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        expected = {
            "academy_id": 1,
            "cohort_id": 1,
            "expires_at": None,
            "id": 1,
            "layout_id": 1,
            "preview_url": None,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": strings[model["cohort"].language]["Main Instructor"],
            "specialty_id": 1,
            "status": "PERSISTED",
            "status_text": "Certificate successfully queued for PDF generation",
            "user_id": 1,
            "is_cleaned": True,
            "update_hash": self.generate_update_hash(user_specialty),
        }

        self.assertToken(result["token"])
        token = result["token"]
        del result["token"]

        self.assertEqual(result, expected)
        del expected["is_cleaned"]

        self.assertEqual(
            self.clear_preview_url(self.bc.database.list_of("certificate.UserSpecialty")),
            [{**expected, "token": token, "issued_at": issued_at}],
        )

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__lang_es__never_ends_true__stage_deleted(self):
        stage = "DELETED"
        cohort_kwargs = {"stage": stage, "current_day": 1, "language": "es", "never_ends": True}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE", "educational_status": "GRADUATED"}
        syllabus_kwargs = {"duration_in_days": 9545799}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
            syllabus_kwargs=syllabus_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        self.generate_models(user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base)

        signals.user_specialty_saved.send_robust.call_args_list = []

        with pytest.raises(ValidationException, match="missing-cohort-user"):
            self.remove_dinamics_fields(generate_certificate(model["user"], model["cohort"]).__dict__)

        self.assertEqual(self.clear_preview_url(self.bc.database.list_of("certificate.UserSpecialty")), [])
        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Retry generate certificate
    """

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate__retry_generate_certificate(self):
        cohort_kwargs = {"stage": "ENDED", "current_day": 9545799}
        cohort_user_kwargs = {"finantial_status": "UP_TO_DATE", "educational_status": "GRADUATED"}
        syllabus_kwargs = {"duration_in_days": 9545799}
        user_specialty_kwargs = {"status": "PERSISTED"}
        model = self.generate_models(
            user=True,
            cohort=True,
            cohort_user=True,
            syllabus_version=True,
            syllabus=True,
            syllabus_schedule=True,
            specialty=True,
            layout_design=True,
            user_specialty=True,
            cohort_kwargs=cohort_kwargs,
            cohort_user_kwargs=cohort_user_kwargs,
            syllabus_kwargs=syllabus_kwargs,
            user_specialty_kwargs=user_specialty_kwargs,
        )

        base = model.copy()
        del base["user"]
        del base["cohort_user"]

        cohort_user_kwargs = {"role": "TEACHER"}
        self.generate_models(user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base)

        try:
            generate_certificate(model["user"], model["cohort"])
            assert False
        except Exception as e:
            self.assertEqual(str(e), "already-exists")

        user_specialty = self.model_to_dict(model, "user_specialty")
        del user_specialty["is_cleaned"]

        self.assertEqual(self.bc.database.list_of("certificate.UserSpecialty"), [user_specialty])

        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                call(instance=user_specialty, sender=user_specialty.__class__),
            ],
        )

"""
Test /certificate
"""

from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

import breathecode.certificate.signals as signals
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_blob_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_client_mock,
)

from ..mixins import CertificateTestCase


class CertificateTestSuite(CertificateTestCase):
    """Test /certificate/cohort/id/student/id"""

    """
    🔽🔽🔽 Post Method
    """

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate_no_default_layout(self):
        """No main teacher in cohort"""
        self.headers(academy=1)
        cohort_user_kwargs = {"role": "STUDENT"}
        base = self.generate_models(
            authenticate=True,
            capability="crud_certificate",
            profile_academy=True,
            role="potato",
            cohort=True,
            user=True,
            cohort_user=True,
            syllabus_schedule=True,
            syllabus=True,
            syllabus_version=True,
            specialty=True,
            cohort_user_kwargs=cohort_user_kwargs,
        )

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )

        url = reverse_lazy("certificate:cohort_id_student_id", kwargs={"cohort_id": 1, "student_id": 1})
        response = self.client.post(url, format="json")
        json = response.json()
        expected = {"detail": "no-default-layout", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate_no_cohort_user(self):
        """No main teacher in cohort"""
        self.headers(academy=1)
        base = self.generate_models(
            authenticate=True,
            cohort=True,
            user=True,
            profile_academy=True,
            capability="crud_certificate",
            role="POTATO",
            syllabus=True,
            specialty=True,
        )

        cohort_user_kwargs = {"role": "TEACHER"}
        teacher_model = self.generate_models(
            user=True, cohort_user=True, cohort_user_kwargs=cohort_user_kwargs, models=base
        )

        url = reverse_lazy("certificate:cohort_id_student_id", kwargs={"cohort_id": 1, "student_id": 1})
        response = self.client.post(url, format="json")
        json = response.json()
        expected = {"detail": "student-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_user_specialty_dict(), [])

        self.assertEqual(signals.user_specialty_saved.send_robust.call_args_list, [])

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock())
    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    @patch("breathecode.certificate.signals.user_specialty_saved.send_robust", MagicMock())
    @patch("django.db.models.signals.pre_delete.send_robust", MagicMock(return_value=None))
    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_generate_certificate(self):
        """No main teacher in cohort"""
        self.headers(academy=1)
        cohort_kwargs = {"stage": "ENDED", "current_day": 112113114115}
        syllabus_kwargs = {"duration_in_days": 112113114115}
        user_specialty_kwargs = {"status": "ERROR"}
        cohort_user_kwargs = {"educational_status": "GRADUATED", "finantial_status": "UP_TO_DATE"}
        model = self.generate_models(
            authenticate=True,
            cohort=True,
            user=True,
            profile_academy=True,
            capability="crud_certificate",
            role="STUDENT",
            cohort_user=True,
            syllabus=True,
            syllabus_version=True,
            syllabus_schedule=True,
            specialty=True,
            user_specialty=True,
            layout_design=True,
            cohort_kwargs=cohort_kwargs,
            user_specialty_kwargs=user_specialty_kwargs,
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

        url = reverse_lazy("certificate:cohort_id_student_id", kwargs={"cohort_id": 1, "student_id": 1})
        data = {"layout_slug": "vanilla"}
        start = timezone.now()
        response = self.client.post(url, data, format="json")

        end = timezone.now()
        json = response.json()
        self.assertDatetime(json["updated_at"])
        del json["updated_at"]

        issued_at = self.iso_to_datetime(json["issued_at"])
        self.assertGreater(issued_at, start)
        self.assertLess(issued_at, end)
        del json["issued_at"]

        expected = {
            "academy": {
                "id": 1,
                "logo_url": model["academy"].logo_url,
                "name": model["academy"].name,
                "slug": model["academy"].slug,
                "website_url": None,
            },
            "cohort": {
                "id": 1,
                "kickoff_date": self.datetime_to_iso(model.cohort.kickoff_date),
                "ending_date": None,
                "name": model["cohort"].name,
                "slug": model["cohort"].slug,
                "schedule": {
                    "id": 1,
                    "name": model["syllabus_schedule"].name,
                    "syllabus": model["syllabus_schedule"].syllabus.id,
                },
                "syllabus_version": {
                    "version": model["syllabus_version"].version,
                    "name": model["syllabus_version"].syllabus.name,
                    "slug": model["syllabus_version"].syllabus.slug,
                    "syllabus": model["syllabus_version"].syllabus.id,
                    "duration_in_days": model["syllabus_version"].syllabus.duration_in_days,
                    "duration_in_hours": model["syllabus_version"].syllabus.duration_in_hours,
                    "week_hours": model["syllabus_version"].syllabus.week_hours,
                },
            },
            "created_at": self.datetime_to_iso(model["user_specialty"].created_at),
            "expires_at": model["user_specialty"].expires_at,
            "id": 1,
            "layout": {
                "name": model["layout_design"].name,
                "background_url": model["layout_design"].background_url,
                "slug": model["layout_design"].slug,
                "foot_note": model["layout_design"].foot_note,
            },
            "preview_url": model["user_specialty"].preview_url,
            "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
            "signed_by_role": "Director",
            "specialty": {
                "description": None,
                "created_at": self.datetime_to_iso(model["specialty"].created_at),
                "id": 1,
                "logo_url": None,
                "name": model["specialty"].name,
                "slug": model["specialty"].slug,
                "updated_at": self.datetime_to_iso(model["specialty"].updated_at),
            },
            "status": "PERSISTED",
            "status_text": "Certificate successfully queued for PDF generation",
            "user": {"first_name": model["user"].first_name, "id": 1, "last_name": model["user"].last_name},
            "profile_academy": {
                "first_name": model["profile_academy"].first_name,
                "id": model["profile_academy"].id,
                "last_name": model["profile_academy"].last_name,
                "status": model["profile_academy"].status,
                "phone": model["profile_academy"].phone,
                "created_at": self.datetime_to_iso(model["profile_academy"].created_at),
                "email": model["profile_academy"].email,
                "academy": {
                    "id": 1,
                    "name": model["academy"].name,
                    "slug": model["academy"].slug,
                },
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_specialty = self.bc.database.get("certificate.UserSpecialty", 1, dict=False)
        self.assertEqual(
            self.all_user_specialty_dict(),
            [
                {
                    "academy_id": 1,
                    "cohort_id": 1,
                    "expires_at": None,
                    "id": 1,
                    "layout_id": 1,
                    "preview_url": model["user_specialty"].preview_url,
                    "signed_by": teacher_model["user"].first_name + " " + teacher_model["user"].last_name,
                    "signed_by_role": "Director",
                    "specialty_id": 1,
                    "status": "PERSISTED",
                    "issued_at": issued_at,
                    "status_text": "Certificate successfully queued for PDF generation",
                    "token": "9e76a2ab3bd55454c384e0a5cdb5298d17285949",
                    "user_id": 1,
                    "update_hash": user_specialty.update_hash,
                }
            ],
        )

        self.assertEqual(
            signals.user_specialty_saved.send_robust.call_args_list,
            [
                # Mixer
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
                # Action
                call(instance=model.user_specialty, sender=model.user_specialty.__class__),
            ],
        )

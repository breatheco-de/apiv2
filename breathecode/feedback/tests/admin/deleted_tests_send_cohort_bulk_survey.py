"""
Test /answer
"""

from datetime import datetime
from unittest.mock import patch
from django.http.request import HttpRequest
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import FeedbackTestCase
from ...admin import send_cohort_bulk_survey
from ...models import Cohort


# TODO: reimplement this test based in Survey model
class SendSurveyTestSuite(FeedbackTestCase):
    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_without_cohort(self):
        """Test /answer without auth"""
        request = HttpRequest()

        self.assertEqual(send_cohort_bulk_survey(None, request, Cohort.objects.all()), None)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_with_educational_status_active(self):
        """Test /answer without auth"""
        request = HttpRequest()

        cohort_kwargs = {"language": "en"}
        cohort_user_kwargs = {"role": "STUDENT", "educational_status": "ACTIVE"}
        models = [
            self.generate_models(
                user=True,
                cohort_user=True,
                profile_academy=True,
                cohort_user_kwargs=cohort_user_kwargs,
                cohort_kwargs=cohort_kwargs,
            )
            for _ in range(0, 3)
        ]
        _cohorts = [(models[key]["cohort"].certificate.name, key + 1) for key in range(0, 3)]
        self.assertEqual(send_cohort_bulk_survey(None, request, Cohort.objects.all()), None)
        expected = [
            {
                "academy_id": None,
                "cohort_id": key,
                "comment": None,
                "event_id": None,
                "highest": "very good",
                "id": key,
                "lang": "en",
                "lowest": "not good",
                "mentor_id": None,
                "opened_at": None,
                "score": None,
                "status": "SENT",
                "survey_id": None,
                "title": f"How has been your experience studying {c} so far?",
                "token_id": key,
                "user_id": key,
            }
            for c, key in _cohorts
        ]

        dicts = [
            answer
            for answer in self.bc.database.list_of("feedback.Answer")
            if isinstance(answer["created_at"], datetime) and answer.pop("created_at")
        ]
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_with_educational_status_graduated(self):
        """Test /answer without auth"""
        request = HttpRequest()

        cohort_kwargs = {"language": "en"}
        cohort_user_kwargs = {"role": "STUDENT", "educational_status": "GRADUATED"}
        models = [
            self.generate_models(
                user=True,
                cohort_user=True,
                profile_academy=True,
                cohort_kwargs=cohort_kwargs,
                cohort_user_kwargs=cohort_user_kwargs,
            )
            for _ in range(0, 3)
        ]
        cohorts = Cohort.objects.all()
        self.assertEqual(send_cohort_bulk_survey(None, request, cohorts), None)
        _cohorts = [(models[key]["cohort"].certificate.name, key + 1) for key in range(0, 3)]
        expected = [
            {
                "academy_id": None,
                "cohort_id": key,
                "comment": None,
                "event_id": None,
                "highest": "very good",
                "id": key,
                "lang": "en",
                "lowest": "not good",
                "mentor_id": None,
                "opened_at": None,
                "score": None,
                "survey_id": None,
                "status": "SENT",
                "title": f"How has been your experience studying {cohort} so far?",
                "token_id": key,
                "user_id": key,
            }
            for cohort, key in _cohorts
        ]

        dicts = [
            answer
            for answer in self.bc.database.list_of("feedback.Answer")
            if isinstance(answer["created_at"], datetime) and answer.pop("created_at")
        ]
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_with_educational_status_postponed(self):
        """Test /answer without auth"""
        request = HttpRequest()

        cohort_kwargs = {"language": "en"}
        cohort_user_kwargs = {"role": "STUDENT", "educational_status": "POSTPONED"}
        for _ in range(0, 3):
            self.generate_models(
                user=True,
                cohort_user=True,
                profile_academy=True,
                cohort_kwargs=cohort_kwargs,
                cohort_user_kwargs=cohort_user_kwargs,
            )

        self.assertEqual(send_cohort_bulk_survey(None, request, Cohort.objects.all()), None)
        expected = []

        dicts = [
            answer
            for answer in self.bc.database.list_of("feedback.Answer")
            if isinstance(answer["created_at"], datetime) and answer.pop("created_at")
        ]
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_with_educational_status_suspended(self):
        """Test /answer without auth"""
        request = HttpRequest()

        cohort_kwargs = {"language": "en"}
        cohort_user_kwargs = {"role": "STUDENT", "educational_status": "SUSPENDED"}
        for _ in range(0, 3):
            self.generate_models(
                user=True,
                cohort_user=True,
                profile_academy=True,
                cohort_kwargs=cohort_kwargs,
                cohort_user_kwargs=cohort_user_kwargs,
            )

        self.assertEqual(send_cohort_bulk_survey(None, request, Cohort.objects.all()), None)
        expected = []

        dicts = [
            answer
            for answer in self.bc.database.list_of("feedback.Answer")
            if isinstance(answer["created_at"], datetime) and answer.pop("created_at")
        ]
        self.assertEqual(dicts, expected)

    @patch(GOOGLE_CLOUD_PATH["client"], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH["bucket"], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH["blob"], apply_google_cloud_blob_mock())
    def test_send_cohort_bulk_survey_with_educational_status_dropped(self):
        """Test /answer without auth"""
        request = HttpRequest()

        cohort_kwargs = {"language": "en"}
        cohort_user_kwargs = {"role": "STUDENT", "educational_status": "DROPPED"}
        for _ in range(0, 3):
            self.generate_models(
                user=True,
                cohort_user=True,
                profile_academy=True,
                cohort_kwargs=cohort_kwargs,
                cohort_user_kwargs=cohort_user_kwargs,
            )

        self.assertEqual(send_cohort_bulk_survey(None, request, Cohort.objects.all()), None)
        expected = []

        dicts = [
            answer
            for answer in self.bc.database.list_of("feedback.Answer")
            if isinstance(answer["created_at"], datetime) and answer.pop("created_at")
        ]
        self.assertEqual(dicts, expected)

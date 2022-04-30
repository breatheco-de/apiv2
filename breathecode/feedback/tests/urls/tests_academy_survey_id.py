"""
Test /academy/survey
"""
import re, urllib
from unittest.mock import patch, MagicMock, call
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import FeedbackTestCase


class SurveyTestSuite(FeedbackTestCase):
    """Test /academy/survey"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__without_auth(self):
        """Test /academy/survey get without authorization"""
        url = reverse_lazy('feedback:academy_survey_id', kwargs={'survey_id': 1})
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__without_academy(self):
        """Test /academy/survey get without academy"""
        self.bc.database.create(authenticate=True)
        url = reverse_lazy('feedback:academy_survey_id', kwargs={'survey_id': 1})
        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """DELETE Auth"""

    def test_academy_survey__delete__in_bulk_without_capability(self):
        """Test /academy/survey/ delete in bulk without capability."""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True, )
        url = reverse_lazy('feedback:academy_survey_id', kwargs={'survey_id': 1})
        response = self.client.delete(url)
        json = response.json()
        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: crud_survey for academy 1",
            'status_code': 403,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_survey_delete_in_bulk_with_two_surveys(self):
        """Test /academy/survey/ delete in bulk with two surveys."""
        self.headers(academy=1)

        model = self.generate_models(user=1, profile_academy=True, survey=2, capability='crud_survey', role=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('feedback:academy_survey_id', kwargs={'survey_id': 1}) + '?id=1,2'
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'survey-id-and-lookups-together', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), self.bc.format.to_dict(model.survey))

    def test_academy_survey_id__delete(self):
        """Test /academy/survey_id delete."""
        self.headers(academy=1)

        model = self.generate_models(user=1, profile_academy=True, survey=1, capability='crud_survey', role=1)

        self.bc.request.authenticate(model.user)

        url = reverse_lazy('feedback:academy_survey_id', kwargs={'survey_id': 1})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [])

    def test_academy_survey_id__delete__not_found(self):
        """Test /academy/survey_id/ delete not found."""
        self.headers(academy=1)

        model = self.generate_models(user=1, profile_academy=True, capability='crud_survey', role=1)

        self.bc.request.authenticate(model.user)

        url = reverse_lazy('feedback:academy_survey_id', kwargs={'survey_id': 1})
        response = self.client.delete(url)
        json = response.json()
        expected = {'detail': 'survey-not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [])

    def test_academy_survey_id__delete__not_answered(self):
        """Test /academy/survey_id/ delete not answered."""
        SURVEY_STATUS = ['PENDING', 'SENT', 'OPENED', 'EXPIRED']

        for x in SURVEY_STATUS:

            answer = {'status': x}
            model = self.generate_models(user=1,
                                         profile_academy=True,
                                         survey=1,
                                         capability='crud_survey',
                                         role=1,
                                         answer=answer)

            self.headers(academy=model.academy.id)

            self.bc.request.authenticate(model.user)

            url = reverse_lazy('feedback:academy_survey_id', kwargs={'survey_id': model.survey.id})
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.bc.database.list_of('feedback.Survey'), [])

    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_academy_survey_id__delete__answered(self):
        """Test /academy/survey_id delete answered(self)."""
        self.headers(academy=1)

        answer = {'status': 'ANSWERED'}
        model = self.generate_models(user=1,
                                     profile_academy=True,
                                     survey=1,
                                     capability='crud_survey',
                                     role=1,
                                     answer=answer)

        self.bc.request.authenticate(model.user)

        url = reverse_lazy('feedback:academy_survey_id', kwargs={'survey_id': 1})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [self.bc.format.to_dict(model.survey)])

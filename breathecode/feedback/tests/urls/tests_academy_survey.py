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
        """Test /academy/survey without authorization"""
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__without_academy(self):
        """Test /academy/survey without academy"""
        self.bc.database.create(authenticate=True)
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__without_role(self):
        """Test /academy/survey without role"""
        self.headers(academy=1)
        url = reverse_lazy('feedback:academy_survey')
        self.bc.database.create(authenticate=True)
        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_survey for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__without_data(self):
        """Test /academy/survey without data"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_data(self):
        """Test /academy/survey with data"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['survey'].id,
            'lang': model['survey'].lang,
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name
            },
            'avg_score': model['survey'].avg_score,
            'response_rate': model['survey'].response_rate,
            'status': model['survey'].status,
            'status_json': model['survey'].status_json,
            'duration': '86400.0',
            'created_at': self.bc.datetime.to_iso_string(model['survey'].created_at),
            'sent_at': None,
            'public_url': 'https://nps.breatheco.de/survey/1'
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_response_rate(self):
        """Test /academy/survey wiith response rate"""

        self.headers(academy=1)
        survey_kwargs = {'response_rate': 7.5}
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=survey_kwargs,
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['survey'].id,
            'lang': model['survey'].lang,
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name
            },
            'avg_score': model['survey'].avg_score,
            'response_rate': model['survey'].response_rate,
            'status': model['survey'].status,
            'status_json': model['survey'].status_json,
            'duration': '86400.0',
            'created_at': self.bc.datetime.to_iso_string(model['survey'].created_at),
            'sent_at': None,
            'public_url': 'https://nps.breatheco.de/survey/1'
        }]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_sent_status_query(self):
        """Test /academy/survey with sent status query"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey') + '?status=SENT'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_pending_status_query(self):
        """Test /academy/survey with pending status query"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey') + '?status=PENDING'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['survey'].id,
            'lang': model['survey'].lang,
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name
            },
            'avg_score': model['survey'].avg_score,
            'response_rate': model['survey'].response_rate,
            'status': model['survey'].status,
            'status_json': model['survey'].status_json,
            'duration': '86400.0',
            'created_at': self.bc.datetime.to_iso_string(model['survey'].created_at),
            'sent_at': None,
            'public_url': 'https://nps.breatheco.de/survey/1'
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_different_lang_query(self):
        """Test /academy/survey with different lang status query"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey') + '?lang=esp'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_same_lang_query(self):
        """Test /academy/survey with same lang status query"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
        )

        url = reverse_lazy('feedback:academy_survey') + '?lang=en'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['survey'].id,
            'lang': model['survey'].lang,
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name
            },
            'avg_score': model['survey'].avg_score,
            'response_rate': model['survey'].response_rate,
            'status': model['survey'].status,
            'status_json': model['survey'].status_json,
            'duration': '86400.0',
            'created_at': self.bc.datetime.to_iso_string(model['survey'].created_at),
            'sent_at': None,
            'public_url': 'https://nps.breatheco.de/survey/1'
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_different_cohort_slug_cohort_query(self):
        """Test /academy/survey with different cohort slug than what is in the cohort query"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
            cohort=True,
        )

        url = reverse_lazy('feedback:academy_survey') + f'?cohort=testing-cohort'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__get__with_same_cohort_slug_cohort_query(self):
        """Test /academy/survey with same cohort slug as in the model"""

        self.headers(academy=1)
        cohort_kwargs = {'slug': 'testing-cohort'}
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='read_survey',
            survey=True,
            capability='read_survey',
            cohort=cohort_kwargs,
        )

        url = reverse_lazy('feedback:academy_survey') + f'?cohort=testing-cohort'
        response = self.client.get(url)
        json = response.json()
        expected = [{
            'id': model['survey'].id,
            'lang': model['survey'].lang,
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name
            },
            'avg_score': model['survey'].avg_score,
            'response_rate': model['survey'].response_rate,
            'status': model['survey'].status,
            'status_json': model['survey'].status_json,
            'duration': '86400.0',
            'created_at': self.bc.datetime.to_iso_string(model['survey'].created_at),
            'sent_at': None,
            'public_url': 'https://nps.breatheco.de/survey/1'
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__without_auth(self):
        """Test /academy/survey without authorization"""
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url, {})
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__without_academy(self):
        """Test /academy/survey without authorization"""
        self.bc.database.create(authenticate=True)
        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url, {})
        json = response.json()
        expected = {
            'detail': "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__without_role(self):
        """Test /academy/survey without role"""
        self.headers(academy=1)
        url = reverse_lazy('feedback:academy_survey')
        self.bc.database.create(authenticate=True)
        response = self.client.post(url, {})
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: crud_survey for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__without_cohort(self):
        """Test /academy/survey post without cohort"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='crud_survey',
            capability='crud_survey',
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url)
        json = response.json()
        expected = {'cohort': ['This field is required.']}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__with_cohort_needs_rights(self):
        """Test /academy/survey post with cohort needs rights"""

        self.headers(academy=2)
        profile_academy_kwargs = {'academy_id': 2}
        model = self.bc.database.create(
            authenticate=True,
            academy=2,
            profile_academy=profile_academy_kwargs,
            role='crud_survey',
            capability='crud_survey',
            cohort=True,
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url, {'cohort': 1})
        json = response.json()
        expected = {'detail': 'cohort-academy-needs-rights', 'status_code': 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__with_cohort_shorter_than_hour(self):
        """Test /academy/survey post with cohort shorter than hour"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='crud_survey',
            capability='crud_survey',
            cohort=True,
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url, {'cohort': 1, 'duration': '3599'})
        json = response.json()
        expected = {'detail': 'minimum-survey-duration-1h', 'status_code': 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__without_cohort_teacher_assigned(self):
        """Test /academy/survey post without cohort teacher assigned"""

        self.headers(academy=1)
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='crud_survey',
            capability='crud_survey',
            cohort=True,
            cohort_user=True,
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url, {'cohort': 1})
        json = response.json()
        expected = {'detail': 'cohort-needs-teacher-assigned', 'status_code': 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__with_cohort_teacher_assigned(self):
        """Test /academy/survey post with cohort teacher assigned"""

        self.headers(academy=1)
        cohort_user_kwargs = [{'role': 'STUDENT'}, {'role': 'TEACHER'}]
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='STUDENT',
            capability='crud_survey',
            cohort=True,
            cohort_user=cohort_user_kwargs,
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url, {'cohort': 1})
        json = response.json()
        del json['created_at']
        del json['updated_at']

        expected = {
            'id': model['cohort'].id,
            'status': True,
            'public_url': 'https://nps.breatheco.de/survey/1',
            'lang': 'en',
            'max_assistants_to_ask': 2,
            'max_teachers_to_ask': 1,
            'duration': '1 00:00:00',
            'sent_at': None,
            'cohort': model['cohort_user'][0].cohort.id,
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_academy_survey__post__with_cohort_teacher_assigned_with_longer_than_hour(self):
        """Test /academy/survey post with cohort teacher assigned with longer than hour."""

        self.headers(academy=1)
        cohort_user_kwargs = [{'role': 'STUDENT'}, {'role': 'TEACHER'}]
        model = self.bc.database.create(
            authenticate=True,
            academy=True,
            profile_academy=True,
            role='STUDENT',
            capability='crud_survey',
            cohort=True,
            cohort_user=cohort_user_kwargs,
        )

        url = reverse_lazy('feedback:academy_survey')
        response = self.client.post(url, {'cohort': 1, 'duration': '3601'})
        json = response.json()
        del json['created_at']
        del json['updated_at']

        expected = {
            'id': model['cohort'].id,
            'status': True,
            'public_url': 'https://nps.breatheco.de/survey/1',
            'lang': 'en',
            'max_assistants_to_ask': 2,
            'max_teachers_to_ask': 1,
            'duration': '01:00:01',
            'sent_at': None,
            'cohort': model['cohort_user'][0].cohort.id,
        }
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """DELETE Auth"""

    def test_academy_survey__delete__in_bulk_without_capability(self):
        """Test /academy/survey delete in bulk without capability."""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True, )
        url = reverse_lazy('feedback:academy_survey')
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

        model = self.generate_models(authenticate=True,
                                     profile_academy=True,
                                     survey=2,
                                     capability='crud_survey',
                                     role=1)

        url = reverse_lazy('feedback:academy_survey') + '?id=1,2'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [])

    def test_academy_survey__delete__without_passing_ids(self):
        """Test /academy/survey/ delete without passing ids."""
        self.headers(academy=1)

        slug = 'without-survey-id-and-lookups'

        model = self.generate_models(user=1, profile_academy=True, survey=2, capability='crud_survey', role=1)

        self.bc.request.authenticate(model.user)
        url = reverse_lazy('feedback:academy_survey')

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['detail'], slug)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), self.bc.format.to_dict(model.survey))

    def test_academy_survey_id__delete__not_answered(self):
        """Test /academy/survey/ id delete not answered."""

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

            url = reverse_lazy('feedback:academy_survey') + f'?id={model.survey.id}'
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self.bc.database.list_of('feedback.Survey'), [])

    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    def test_academy_survey_id__delete__answered(self):
        """Test /academy/survey/ id delete answered."""
        self.headers(academy=1)

        answer = {'status': 'ANSWERED'}
        model = self.generate_models(user=1,
                                     profile_academy=True,
                                     survey=1,
                                     capability='crud_survey',
                                     role=1,
                                     answer=answer)

        self.bc.request.authenticate(model.user)

        url = reverse_lazy('feedback:academy_survey') + '?id=1'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('feedback.Survey'), [self.bc.format.to_dict(model.survey)])

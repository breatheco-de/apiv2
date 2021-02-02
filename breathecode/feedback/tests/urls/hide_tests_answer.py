"""
Test /answer
"""
import re, urllib
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import FeedbackTestCase

class AnswerTestSuite(FeedbackTestCase):
    """Test /answer"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_without_auth(self):
        """Test /answer without auth"""
        url = reverse_lazy('feedback:answer')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_wrong_academy(self):
        """Test /answer without auth"""
        url = reverse_lazy('feedback:answer')
        response = self.client.get(url, **{'HTTP_Academy': 1 })
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_without_data(self):
        """Test /answer without auth"""
        models = self.generate_models(authenticate=True, profile_academy=True)
        url = reverse_lazy('feedback:answer')
        response = self.client.get(url, **{'HTTP_Academy': models['profile_academy'].academy.id })
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_answer(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_data(self):
        """Test /answer without auth"""
        model = self.generate_models(authenticate=True, answer=True)
        db = self.model_to_dict(model, 'answer')
        url = reverse_lazy('feedback:answer')
        response = self.client.get(url, academy=model['answer'].academy.id)
        json = response.json()

        self.assertEqual(json, [{
            'academy': model['answer'].academy,
            'cohort': model['answer'].cohort,
            'comment': model['answer'].comment,
            'event': model['answer'].event,
            'highest': model['answer'].highest,
            'id': model['answer'].id,
            'lang': model['answer'].lang,
            'lowest': model['answer'].lowest,
            'mentor': model['answer'].mentor,
            'score': model['answer'].score,
            'status': model['answer'].status,
            'title': model['answer'].title,
            'user': model['answer'].user,
        }])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_bad_param_user_with_data(self):
        """Test /answer without auth"""
        model = self.generate_models(authenticate=True, user=True, answer=True)
        db = self.model_to_dict(model, 'answer')
        print(model['user'].id)
        params = {
            'user': 9999,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url, headers={"Academy": model['answer'].academy.id})
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_param_user_with_data(self):
        """Test /answer without auth"""
        model = self.generate_models(authenticate=True, user=True, answer=True)
        db = self.model_to_dict(model, 'answer')
        print(model['user'].id)
        params = {
            'user': model['user'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url, headers={"Academy": model['answer'].academy.id })
        json = response.json()

        self.assertEqual(json, [{
            'cohort': model['answer'].cohort,
            'comment': model['answer'].comment,
            'event': model['answer'].event,
            'highest': model['answer'].highest,
            'id': model['answer'].id,
            'lang': model['answer'].lang,
            'lowest': model['answer'].lowest,
            'mentor': model['answer'].mentor,
            'score': model['answer'].score,
            'status': model['answer'].status,
            'title': model['answer'].title,
            'user': {
                'first_name': model['user'].first_name,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
            },
        }])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_bad_param_cohort_with_data(self):
        """Test /answer without auth"""
        model = self.generate_models(authenticate=True, user=True, cohort=True, answer=True)
        db = self.model_to_dict(model, 'answer')
        params = {
            'cohort': 'they-killed-kenny',
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url, headers={"Academy": model['answer'].academy.id})
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_param_cohort_with_data(self):
        """Test /answer without auth"""
        model = self.generate_models(authenticate=True, user=True, cohort=True, answer=True)
        db = self.model_to_dict(model, 'answer')
        params = {
            'cohort': model['cohort'].slug,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url, headers={"Academy": model['answer'].academy.id})
        json = response.json()

        self.assertEqual(json, [{
            'academy': model['answer'].academy,
            'cohort': {
                'id': model['cohort'].id,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
            },
            'comment': model['answer'].comment,
            'event': model['answer'].event,
            'highest': model['answer'].highest,
            'id': model['answer'].id,
            'lang': model['answer'].lang,
            'lowest': model['answer'].lowest,
            'mentor': model['answer'].mentor,
            'score': model['answer'].score,
            'status': model['answer'].status,
            'title': model['answer'].title,
            'user': {
                'first_name': model['user'].first_name,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
            },
        }])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_param_academy_with_data(self):
        """Test /answer without auth"""
        model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            answer=True)
        db = self.model_to_dict(model, 'answer')
        params = {
            'academy': model['academy'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url, headers={"Academy": model['academy'].id})
        json = response.json()

        self.assertEqual(json, [{
            'academy': {
                'id': model['academy'].id,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
            },
            'cohort': {
                'id': model['cohort'].id,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
            },
            'comment': model['answer'].comment,
            'event': model['answer'].event,
            'highest': model['answer'].highest,
            'id': model['answer'].id,
            'lang': model['answer'].lang,
            'lowest': model['answer'].lowest,
            'mentor': model['answer'].mentor,
            'score': model['answer'].score,
            'status': model['answer'].status,
            'title': model['answer'].title,
            'user': {
                'first_name': model['user'].first_name,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
            },
        }])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_bad_param_mentor_with_data(self):
        """Test /answer without auth"""
        model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            answer=True, mentor=True)
        db = self.model_to_dict(model, 'answer')
        params = {
            'mentor': 9999,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_param_mentor_with_data(self):
        """Test /answer without auth"""
        model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            answer=True, mentor=True)
        db = self.model_to_dict(model, 'answer')
        params = {
            'mentor': model['mentor'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url, headers={"Academy": model['academy'].id})
        json = response.json()

        self.assertEqual(json, [{
            'academy': {
                'id': model['academy'].id,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
            },
            'cohort': {
                'id': model['cohort'].id,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
            },
            'comment': model['answer'].comment,
            'event': model['answer'].event,
            'highest': model['answer'].highest,
            'id': model['answer'].id,
            'lang': model['answer'].lang,
            'lowest': model['answer'].lowest,
            'mentor': {
                'first_name': model['mentor'].first_name,
                'id': model['mentor'].id,
                'last_name': model['mentor'].last_name,
            },
            'score': model['answer'].score,
            'status': model['answer'].status,
            'title': model['answer'].title,
            'user': {
                'first_name': model['user'].first_name,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
            },
        }])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_bad_param_event_with_data(self):
        """Test /answer without auth"""
        model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            answer=True, mentor=True, event=True)
        db = self.model_to_dict(model, 'answer')
        params = {
            'event': 9999,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_param_event_with_data(self):
        """Test /answer without auth"""
        model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            answer=True, mentor=True, event=True)
        db = self.model_to_dict(model, 'answer')
        params = {
            'event': model['event'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [{
            'academy': {
                'id': model['academy'].id,
                'name': model['academy'].name,
                'slug': model['academy'].slug,
            },
            'cohort': {
                'id': model['cohort'].id,
                'name': model['cohort'].name,
                'slug': model['cohort'].slug,
            },
            'comment': model['answer'].comment,
            'event': {
                'id': model['event'].id,
                'description': model['event'].description,
                'excerpt': model['event'].excerpt,
                'lang': model['event'].lang,
                'title': model['event'].title,
            },
            'highest': model['answer'].highest,
            'id': model['answer'].id,
            'lang': model['answer'].lang,
            'lowest': model['answer'].lowest,
            'mentor': {
                'first_name': model['mentor'].first_name,
                'id': model['mentor'].id,
                'last_name': model['mentor'].last_name,
            },
            'score': model['answer'].score,
            'status': model['answer'].status,
            'title': model['answer'].title,
            'user': {
                'first_name': model['user'].first_name,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
            },
        }])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_bad_param_score_with_data(self):
        """Test /answer without auth"""
        for number in range(1, 10):
            self.remove_all_answer()
            score = str(number)
            model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
                answer=True, mentor=True, event=True, answer_score=score)
            db = self.model_to_dict(model, 'answer')
            params = {
                'score': 1 if number == 10 else number + 1,
            }
            base_url = reverse_lazy('feedback:answer')
            url = f'{base_url}?{urllib.parse.urlencode(params)}'
            response = self.client.get(url)
            json = response.json()

            self.assertEqual(json, [])

            db['score'] = score
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_param_score_with_data(self):
        """Test /answer without auth"""
        for number in range(1, 10):
            self.remove_all_answer()
            score = str(number)
            model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
                answer=True, mentor=True, event=True, answer_score=score)
            db = self.model_to_dict(model, 'answer')
            params = {
                'score': score,
            }
            base_url = reverse_lazy('feedback:answer')
            url = f'{base_url}?{urllib.parse.urlencode(params)}'
            response = self.client.get(url, headers={"Academy", model['academy'].id })
            json = response.json()

            self.assertEqual(json, [{
                'academy': {
                    'id': model['academy'].id,
                    'name': model['academy'].name,
                    'slug': model['academy'].slug,
                },
                'cohort': {
                    'id': model['cohort'].id,
                    'name': model['cohort'].name,
                    'slug': model['cohort'].slug,
                },
                'comment': model['answer'].comment,
                'event': {
                    'id': model['event'].id,
                    'description': model['event'].description,
                    'excerpt': model['event'].excerpt,
                    'lang': model['event'].lang,
                    'title': model['event'].title,
                },
                'highest': model['answer'].highest,
                'id': model['answer'].id,
                'lang': model['answer'].lang,
                'lowest': model['answer'].lowest,
                'mentor': {
                    'first_name': model['mentor'].first_name,
                    'id': model['mentor'].id,
                    'last_name': model['mentor'].last_name,
                },
                'score': score,
                'status': model['answer'].status,
                'title': model['answer'].title,
                'user': {
                    'first_name': model['user'].first_name,
                    'id': model['user'].id,
                    'last_name': model['user'].last_name,
                },
            }])

            db['score'] = score

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.all_answer_dict(), [db])

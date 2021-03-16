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
from ..mixins.new_feedback_test_case import FeedbackTestCase

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

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_wrong_academy(self):
        """Test /answer without auth"""
        url = reverse_lazy('feedback:answer')
        response = self.client.get(url, **{'HTTP_Academy': 1 })
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('feedback:answer')
        self.generate_models(authenticate=True)
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, {
            'detail': "You (user: 1) don't have this capability: read_nps_answers for academy 1",
            'status_code': 403
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True, profile_academy=True,
            capability='read_nps_answers', role='potato')
        url = reverse_lazy('feedback:answer')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_answer(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, answer=True, profile_academy=True,
            capability='read_nps_answers', role='potato')
        db = self.model_to_dict(model, 'answer')
        url = reverse_lazy('feedback:answer')
        response = self.client.get(url)
        json = response.json()

        json = [{**x, 'created_at': None} for x in json if self.assertDatetime(x['created_at'])]

        self.assertEqual(json, [{
            'created_at': None,
            'academy': {
                'id': model['answer'].academy.id,
                'name': model['answer'].academy.name,
                'slug': model['answer'].academy.slug,
            },
            'cohort': {
                'id': model['answer'].cohort.id,
                'name': model['answer'].cohort.name,
                'slug': model['answer'].cohort.slug,
            },
            'comment': model['answer'].comment,
            'event': model['answer'].event,
            'highest': model['answer'].highest,
            'id': model['answer'].id,
            'lang': model['answer'].lang,
            'lowest': model['answer'].lowest,
            'mentor': {
                'first_name':  model['answer'].mentor.first_name,
                'id':  model['answer'].mentor.id,
                'last_name':  model['answer'].mentor.last_name,
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
    def test_answer_with_bad_param_user_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, user=True, answer=True, profile_academy=True,
            capability='read_nps_answers', role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'user': 9999
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
    def test_answer_with_param_user_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, user=True, answer=True, profile_academy=True,
            capability='read_nps_answers', role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'user': model['user'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url)
        json = response.json()

        json = [{**x, 'created_at': None} for x in json if self.assertDatetime(x['created_at'])]

        self.assertEqual(json, [{
            'created_at': None,
            'academy': {
                'id': model['answer'].academy.id,
                'name': model['answer'].academy.name,
                'slug': model['answer'].academy.slug,
            },
            'cohort': {
                'id': model['answer'].cohort.id,
                'name': model['answer'].cohort.name,
                'slug': model['answer'].cohort.slug,
            },
            'comment': model['answer'].comment,
            'event': model['answer'].event,
            'highest': model['answer'].highest,
            'id': model['answer'].id,
            'lang': model['answer'].lang,
            'lowest': model['answer'].lowest,
            'mentor': {
                'first_name':  model['answer'].mentor.first_name,
                'id':  model['answer'].mentor.id,
                'last_name':  model['answer'].mentor.last_name,
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
    def test_answer_with_bad_param_cohort_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, user=True, cohort=True, answer=True, profile_academy=True,
            capability='read_nps_answers', role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'cohort': 'they-killed-kenny',
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
    def test_answer_with_param_cohort_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, user=True, cohort=True, answer=True, profile_academy=True,
            capability='read_nps_answers', role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'cohort': model['cohort'].slug,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url)
        json = response.json()

        json = [{**x, 'created_at': None} for x in json if self.assertDatetime(x['created_at'])]

        self.assertEqual(json, [{
            'created_at': None,
            'academy': {
                'id': model['answer'].academy.id,
                'name': model['answer'].academy.name,
                'slug': model['answer'].academy.slug,
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
                'first_name':  model['answer'].mentor.first_name,
                'id':  model['answer'].mentor.id,
                'last_name':  model['answer'].mentor.last_name,
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
    def test_answer_with_param_academy_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            answer=True, profile_academy=True, capability='read_nps_answers', role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'academy': model['academy'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url)
        json = response.json()

        json = [{**x, 'created_at': None} for x in json if self.assertDatetime(x['created_at'])]

        self.assertEqual(json, [{
            'created_at': None,
            'academy': {
                'id': model['answer'].academy.id,
                'name': model['answer'].academy.name,
                'slug': model['answer'].academy.slug,
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
                'first_name':  model['answer'].mentor.first_name,
                'id':  model['answer'].mentor.id,
                'last_name':  model['answer'].mentor.last_name,
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
    def test_answer_with_bad_param_mentor_with_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            answer=True, profile_academy=True, capability='read_nps_answers',
            role='potato')
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
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            answer=True, profile_academy=True, capability='read_nps_answers',
            role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'mentor': model['user'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url, headers={"Academy": model['academy'].id})
        json = response.json()

        json = [{**x, 'created_at': None} for x in json if self.assertDatetime(x['created_at'])]

        self.assertEqual(json, [{
            'created_at': None,
            'academy': {
                'id': model['answer'].academy.id,
                'name': model['answer'].academy.name,
                'slug': model['answer'].academy.slug,
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
                'first_name': model['user'].first_name,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
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
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            answer=True, event=True, profile_academy=True,
            capability='read_nps_answers', role='potato')
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
        self.headers(academy=1)
        model = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            answer=True, event=True, profile_academy=True,
            capability='read_nps_answers', role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'event': model['event'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url)
        json = response.json()

        json = [{**x, 'created_at': None} for x in json if self.assertDatetime(x['created_at'])]

        self.assertEqual(json, [{
            'created_at': None,
            'academy': {
                'id': model['answer'].academy.id,
                'name': model['answer'].academy.name,
                'slug': model['answer'].academy.slug,
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
                'first_name': model['user'].first_name,
                'id': model['user'].id,
                'last_name': model['user'].last_name,
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
        self.headers(academy=1)
        base = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            event=True, profile_academy=True, capability='read_nps_answers', role='potato')

        for number in range(1, 10):
            self.remove_all_answer()
            score = str(number)

            answer_kwargs = {
                'score': score
            }
            model = self.generate_models(answer=True, answer_kwargs=answer_kwargs, models=base)
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
        self.headers(academy=1)
        base = self.generate_models(authenticate=True, user=True, cohort=True, academy=True,
            event=True, profile_academy=True, capability='read_nps_answers', role='potato')

        for number in range(1, 10):
            self.remove_all_answer()
            score = str(number)

            answer_kwargs = {
                'score': score
            }
            model = self.generate_models(answer=True, answer_kwargs=answer_kwargs, models=base)
            db = self.model_to_dict(model, 'answer')
            params = {
                'score': score,
            }
            base_url = reverse_lazy('feedback:answer')
            url = f'{base_url}?{urllib.parse.urlencode(params)}'
            response = self.client.get(url, headers={"Academy", model['academy'].id })
            json = response.json()

            json = [{**x, 'created_at': None} for x in json if self.assertDatetime(x['created_at'])]

            self.assertEqual(json, [{
                'created_at': None,
                'academy': {
                    'id': model['answer'].academy.id,
                    'name': model['answer'].academy.name,
                    'slug': model['answer'].academy.slug,
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
                    'first_name': model['user'].first_name,
                    'id': model['user'].id,
                    'last_name': model['user'].last_name,
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

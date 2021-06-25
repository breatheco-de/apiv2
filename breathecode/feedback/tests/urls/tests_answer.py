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
        response = self.client.get(url, **{'HTTP_Academy': 1})
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

        self.assertEqual(
            json, {
                'detail':
                "You (user: 1) don't have this capability: read_nps_answers for academy 1",
                'status_code': 403
            })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_without_data(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        models = self.generate_models(authenticate=True,
                                      profile_academy=True,
                                      capability='read_nps_answers',
                                      role='potato')
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
        model = self.generate_models(authenticate=True,
                                     answer=True,
                                     profile_academy=True,
                                     capability='read_nps_answers',
                                     role='potato')
        db = self.model_to_dict(model, 'answer')
        url = reverse_lazy('feedback:answer')
        response = self.client.get(url)
        json = response.json()

        json = [{
            **x, 'created_at': None
        } for x in json if self.assertDatetime(x['created_at'])]

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
                'first_name': model['answer'].mentor.first_name,
                'id': model['answer'].mentor.id,
                'last_name': model['answer'].mentor.last_name,
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
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     answer=True,
                                     profile_academy=True,
                                     capability='read_nps_answers',
                                     role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {'user': 9999}
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
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     answer=True,
                                     profile_academy=True,
                                     capability='read_nps_answers',
                                     role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'user': model['user'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url)
        json = response.json()

        json = [{
            **x, 'created_at': None
        } for x in json if self.assertDatetime(x['created_at'])]

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
                'first_name': model['answer'].mentor.first_name,
                'id': model['answer'].mentor.id,
                'last_name': model['answer'].mentor.last_name,
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
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     cohort=True,
                                     answer=True,
                                     profile_academy=True,
                                     capability='read_nps_answers',
                                     role='potato')
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
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     cohort=True,
                                     answer=True,
                                     profile_academy=True,
                                     capability='read_nps_answers',
                                     role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'cohort': model['cohort'].slug,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url)
        json = response.json()

        json = [{
            **x, 'created_at': None
        } for x in json if self.assertDatetime(x['created_at'])]

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
                'first_name': model['answer'].mentor.first_name,
                'id': model['answer'].mentor.id,
                'last_name': model['answer'].mentor.last_name,
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
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     cohort=True,
                                     academy=True,
                                     answer=True,
                                     profile_academy=True,
                                     capability='read_nps_answers',
                                     role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'academy': model['academy'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url)
        json = response.json()

        json = [{
            **x, 'created_at': None
        } for x in json if self.assertDatetime(x['created_at'])]

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
                'first_name': model['answer'].mentor.first_name,
                'id': model['answer'].mentor.id,
                'last_name': model['answer'].mentor.last_name,
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
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     cohort=True,
                                     academy=True,
                                     answer=True,
                                     profile_academy=True,
                                     capability='read_nps_answers',
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
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     cohort=True,
                                     academy=True,
                                     answer=True,
                                     profile_academy=True,
                                     capability='read_nps_answers',
                                     role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'mentor': model['user'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url,
                                   headers={"Academy": model['academy'].id})
        json = response.json()

        json = [{
            **x, 'created_at': None
        } for x in json if self.assertDatetime(x['created_at'])]

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
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     cohort=True,
                                     academy=True,
                                     answer=True,
                                     event=True,
                                     profile_academy=True,
                                     capability='read_nps_answers',
                                     role='potato')
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
        model = self.generate_models(authenticate=True,
                                     user=True,
                                     cohort=True,
                                     academy=True,
                                     answer=True,
                                     event=True,
                                     profile_academy=True,
                                     capability='read_nps_answers',
                                     role='potato')
        db = self.model_to_dict(model, 'answer')
        params = {
            'event': model['event'].id,
        }
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?{urllib.parse.urlencode(params)}'
        response = self.client.get(url)
        json = response.json()

        json = [{
            **x, 'created_at': None
        } for x in json if self.assertDatetime(x['created_at'])]

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
        base = self.generate_models(authenticate=True,
                                    user=True,
                                    cohort=True,
                                    academy=True,
                                    event=True,
                                    profile_academy=True,
                                    capability='read_nps_answers',
                                    role='potato')

        for number in range(1, 10):
            self.remove_all_answer()
            score = str(number)

            answer_kwargs = {'score': score}
            model = self.generate_models(answer=True,
                                         answer_kwargs=answer_kwargs,
                                         models=base)
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
        base = self.generate_models(authenticate=True,
                                    user=True,
                                    cohort=True,
                                    academy=True,
                                    event=True,
                                    profile_academy=True,
                                    capability='read_nps_answers',
                                    role='potato')

        for number in range(1, 10):
            self.remove_all_answer()
            score = str(number)

            answer_kwargs = {'score': score}
            model = self.generate_models(answer=True,
                                         answer_kwargs=answer_kwargs,
                                         models=base)
            db = self.model_to_dict(model, 'answer')
            params = {
                'score': score,
            }
            base_url = reverse_lazy('feedback:answer')
            url = f'{base_url}?{urllib.parse.urlencode(params)}'
            response = self.client.get(
                url, headers={"Academy", model['academy'].id})
            json = response.json()

            json = [{
                **x, 'created_at': None
            } for x in json if self.assertDatetime(x['created_at'])]

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

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_data_without_pagination_get_just_100(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_nps_answers',
                                    role='potato')

        models = [
            self.generate_models(answer=True, models=base)
            for _ in range(0, 105)
        ]
        ordened_models = sorted(models,
                                key=lambda x: x['answer'].created_at,
                                reverse=True)

        url = reverse_lazy('feedback:answer')
        response = self.client.get(url)
        json = response.json()

        json = [{
            **x, 'created_at': None
        } for x in json if self.assertDatetime(x['created_at'])]

        expected = [{
            'id': model['answer'].id,
            'title': model['answer'].title,
            'lowest': model['answer'].lowest,
            'highest': model['answer'].highest,
            'lang': model['answer'].lang,
            'comment': model['answer'].comment,
            'score': model['answer'].score,
            'status': model['answer'].status,
            'created_at': None,
            'user': {
                'id': model['user'].id,
                'first_name': model['user'].first_name,
                'last_name': model['user'].last_name,
            },
            'academy': {
                'id': model['answer'].academy.id,
                'slug': model['answer'].academy.slug,
                'name': model['answer'].academy.name,
            },
            'cohort': {
                'id': model['answer'].cohort.id,
                'slug': model['answer'].cohort.slug,
                'name': model['answer'].cohort.name,
            },
            'mentor': {
                'id': model['answer'].mentor.id,
                'first_name': model['answer'].mentor.first_name,
                'last_name': model['answer'].mentor.last_name,
            },
            'event': model['answer'].event,
        } for model in ordened_models][:100]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [{
            **self.model_to_dict(model, 'answer'),
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_data_with_pagination_first_five(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_nps_answers',
                                    role='potato')

        models = [
            self.generate_models(answer=True, models=base)
            for _ in range(0, 10)
        ]
        ordened_models = sorted(models,
                                key=lambda x: x['answer'].created_at,
                                reverse=True)

        url = reverse_lazy('feedback:answer') + '?limit=5&offset=0'
        response = self.client.get(url)
        json = response.json()

        prev_results = json['results']
        json['results'] = [{
            **x, 'created_at': None
        } for x in prev_results if self.assertDatetime(x['created_at'])]

        results = [{
            'id': model['answer'].id,
            'title': model['answer'].title,
            'lowest': model['answer'].lowest,
            'highest': model['answer'].highest,
            'lang': model['answer'].lang,
            'comment': model['answer'].comment,
            'score': model['answer'].score,
            'status': model['answer'].status,
            'created_at': None,
            'user': {
                'id': model['user'].id,
                'first_name': model['user'].first_name,
                'last_name': model['user'].last_name,
            },
            'academy': {
                'id': model['answer'].academy.id,
                'slug': model['answer'].academy.slug,
                'name': model['answer'].academy.name,
            },
            'cohort': {
                'id': model['answer'].cohort.id,
                'slug': model['answer'].cohort.slug,
                'name': model['answer'].cohort.name,
            },
            'mentor': {
                'id': model['answer'].mentor.id,
                'first_name': model['answer'].mentor.first_name,
                'last_name': model['answer'].mentor.last_name,
            },
            'event': model['answer'].event,
        } for model in ordened_models][:5]

        expected = {
            'count': 10,
            'first': None,
            'next': 'http://testserver/v1/feedback/academy/answer?limit=5&'
            f'offset=5',
            'previous': None,
            'last': 'http://testserver/v1/feedback/academy/answer?limit=5&'
            f'offset=5',
            'results': results
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [{
            **self.model_to_dict(model, 'answer'),
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_data_with_pagination_last_five(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_nps_answers',
                                    role='potato')

        models = [
            self.generate_models(answer=True, models=base)
            for _ in range(0, 10)
        ]
        ordened_models = sorted(models,
                                key=lambda x: x['answer'].created_at,
                                reverse=True)

        url = reverse_lazy('feedback:answer') + '?limit=5&offset=5'
        response = self.client.get(url)
        json = response.json()

        prev_results = json['results']
        json['results'] = [{
            **x, 'created_at': None
        } for x in prev_results if self.assertDatetime(x['created_at'])]

        results = [{
            'id': model['answer'].id,
            'title': model['answer'].title,
            'lowest': model['answer'].lowest,
            'highest': model['answer'].highest,
            'lang': model['answer'].lang,
            'comment': model['answer'].comment,
            'score': model['answer'].score,
            'status': model['answer'].status,
            'created_at': None,
            'user': {
                'id': model['user'].id,
                'first_name': model['user'].first_name,
                'last_name': model['user'].last_name,
            },
            'academy': {
                'id': model['answer'].academy.id,
                'slug': model['answer'].academy.slug,
                'name': model['answer'].academy.name,
            },
            'cohort': {
                'id': model['answer'].cohort.id,
                'slug': model['answer'].cohort.slug,
                'name': model['answer'].cohort.name,
            },
            'mentor': {
                'id': model['answer'].mentor.id,
                'first_name': model['answer'].mentor.first_name,
                'last_name': model['answer'].mentor.last_name,
            },
            'event': model['answer'].event,
        } for model in ordened_models][5:]

        expected = {
            'count': 10,
            'first': 'http://testserver/v1/feedback/academy/answer?limit=5',
            'next': None,
            'previous': 'http://testserver/v1/feedback/academy/answer?limit=5',
            'last': None,
            'results': results,
        }

        self.assertEqual(json, expected)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [{
            **self.model_to_dict(model, 'answer'),
        } for model in models])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_data_with_pagination_last_five(self):
        """Test /answer without auth"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_nps_answers',
                                    role='potato')

        models = [
            self.generate_models(answer=True, models=base)
            for _ in range(0, 10)
        ]
        url = reverse_lazy('feedback:answer') + '?limit=5&offset=10'
        response = self.client.get(url)
        json = response.json()
        expected = {
            'count': 10,
            'first': 'http://testserver/v1/feedback/academy/answer?limit=5',
            'next': None,
            'previous':
            'http://testserver/v1/feedback/academy/answer?limit=5&offset=5',
            'last': None,
            'results': [],
        }

        self.assertEqual(json, expected)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [{
            **self.model_to_dict(model, 'answer'),
        } for model in models])

    """
    🔽🔽🔽 With full like querystring
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_query_like_full_name(self):
        """Test /answer with like full name"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_nps_answers',
                                    role='potato')
        del base['user']
        user_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Reinaldo',
            'last_name': 'Descarado',
        }
        models = [
            self.generate_models(user=True,
                                 answer=True,
                                 user_kwargs=user_kwargs,
                                 models=base),
            self.generate_models(user=True,
                                 answer=True,
                                 user_kwargs=user_kwargs_2,
                                 models=base),
        ]

        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?like=Rene Descartes'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'created_at':
            self.datetime_to_iso(models[0].answer.created_at),
            'academy': {
                'id': models[0].answer.academy.id,
                'name': models[0].answer.academy.name,
                'slug': models[0].answer.academy.slug,
            },
            'cohort': {
                'id': models[0].cohort.id,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
            },
            'comment':
            models[0].answer.comment,
            'event':
            models[0].answer.event,
            'highest':
            models[0].answer.highest,
            'id':
            models[0].answer.id,
            'lang':
            models[0].answer.lang,
            'lowest':
            models[0].answer.lowest,
            'mentor': {
                'first_name': models[0].answer.mentor.first_name,
                'id': models[0].answer.mentor.id,
                'last_name': models[0].answer.mentor.last_name,
            },
            'score':
            models[0].answer.score,
            'status':
            models[0].answer.status,
            'title':
            models[0].answer.title,
            'user': {
                'first_name': 'Rene',
                'id': 2,
                'last_name': 'Descartes',
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_query_like_first_name(self):
        """Test /answer with like first name"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_nps_answers',
                                    role='potato')
        del base['user']
        user_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Reinaldo',
            'last_name': 'Descarado',
        }
        models = [
            self.generate_models(user=True,
                                 answer=True,
                                 user_kwargs=user_kwargs,
                                 models=base),
            self.generate_models(user=True,
                                 answer=True,
                                 user_kwargs=user_kwargs_2,
                                 models=base),
        ]
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?like=Rene'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'created_at':
            self.datetime_to_iso(models[0].answer.created_at),
            'academy': {
                'id': models[0].answer.academy.id,
                'name': models[0].answer.academy.name,
                'slug': models[0].answer.academy.slug,
            },
            'cohort': {
                'id': models[0].cohort.id,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
            },
            'comment':
            models[0].answer.comment,
            'event':
            models[0].answer.event,
            'highest':
            models[0].answer.highest,
            'id':
            models[0].answer.id,
            'lang':
            models[0].answer.lang,
            'lowest':
            models[0].answer.lowest,
            'mentor': {
                'first_name': models[0].answer.mentor.first_name,
                'id': models[0].answer.mentor.id,
                'last_name': models[0].answer.mentor.last_name,
            },
            'score':
            models[0].answer.score,
            'status':
            models[0].answer.status,
            'title':
            models[0].answer.title,
            'user': {
                'first_name': 'Rene',
                'id': 2,
                'last_name': 'Descartes',
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_query_like_last_name(self):
        """Test /answer with like last name"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_nps_answers',
                                    role='potato')
        del base['user']
        user_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Reinaldo',
            'last_name': 'Descarado',
        }
        models = [
            self.generate_models(user=True,
                                 answer=True,
                                 user_kwargs=user_kwargs,
                                 models=base),
            self.generate_models(user=True,
                                 answer=True,
                                 user_kwargs=user_kwargs_2,
                                 models=base),
        ]
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?like=Descartes'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'created_at':
            self.datetime_to_iso(models[0].answer.created_at),
            'academy': {
                'id': models[0].answer.academy.id,
                'name': models[0].answer.academy.name,
                'slug': models[0].answer.academy.slug,
            },
            'cohort': {
                'id': models[0].cohort.id,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
            },
            'comment':
            models[0].answer.comment,
            'event':
            models[0].answer.event,
            'highest':
            models[0].answer.highest,
            'id':
            models[0].answer.id,
            'lang':
            models[0].answer.lang,
            'lowest':
            models[0].answer.lowest,
            'mentor': {
                'first_name': models[0].answer.mentor.first_name,
                'id': models[0].answer.mentor.id,
                'last_name': models[0].answer.mentor.last_name,
            },
            'score':
            models[0].answer.score,
            'status':
            models[0].answer.status,
            'title':
            models[0].answer.title,
            'user': {
                'first_name': 'Rene',
                'id': 2,
                'last_name': 'Descartes',
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_with_query_like_email(self):
        """Test /answer with like email"""
        self.headers(academy=1)
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    capability='read_nps_answers',
                                    role='potato')
        del base['user']
        user_kwargs = {
            'email': 'b@b.com',
            'first_name': 'Rene',
            'last_name': 'Descartes',
        }
        user_kwargs_2 = {
            'email': 'a@a.com',
            'first_name': 'Reinaldo',
            'last_name': 'Descarado',
        }
        models = [
            self.generate_models(user=True,
                                 answer=True,
                                 user_kwargs=user_kwargs,
                                 models=base),
            self.generate_models(user=True,
                                 answer=True,
                                 user_kwargs=user_kwargs_2,
                                 models=base),
        ]
        base_url = reverse_lazy('feedback:answer')
        url = f'{base_url}?like=b@b.com'

        response = self.client.get(url)
        json = response.json()

        expected = [{
            'created_at':
            self.datetime_to_iso(models[0].answer.created_at),
            'academy': {
                'id': models[0].answer.academy.id,
                'name': models[0].answer.academy.name,
                'slug': models[0].answer.academy.slug,
            },
            'cohort': {
                'id': models[0].cohort.id,
                'name': models[0].cohort.name,
                'slug': models[0].cohort.slug,
            },
            'comment':
            models[0].answer.comment,
            'event':
            models[0].answer.event,
            'highest':
            models[0].answer.highest,
            'id':
            models[0].answer.id,
            'lang':
            models[0].answer.lang,
            'lowest':
            models[0].answer.lowest,
            'mentor': {
                'first_name': models[0].answer.mentor.first_name,
                'id': models[0].answer.mentor.id,
                'last_name': models[0].answer.mentor.last_name,
            },
            'score':
            models[0].answer.score,
            'status':
            models[0].answer.status,
            'title':
            models[0].answer.title,
            'user': {
                'first_name': 'Rene',
                'id': 2,
                'last_name': 'Descartes',
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

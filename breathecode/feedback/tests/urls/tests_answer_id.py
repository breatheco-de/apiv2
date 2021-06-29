"""
Test /answer/:id
"""
import re
from datetime import datetime
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.services.datetime_to_iso_format import datetime_to_iso_format
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import FeedbackTestCase


class AnswerIdTestSuite(FeedbackTestCase):
    """Test /answer/:id"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_without_auth(self):
        """Test /answer/:id without auth"""
        url = reverse_lazy('feedback:answer_id', kwargs={'answer_id': 9999})
        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': 'Authentication credentials were not provided.',
            'status_code': 401
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.count_answer(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_without_data(self):
        """Test /answer/:id without auth"""
        self.generate_models(authenticate=True)
        url = reverse_lazy('feedback:answer_id', kwargs={'answer_id': 9999})
        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': 'This survey does not exist for this user',
            'status_code': 404
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.count_answer(), 0)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_with_data_without_user(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(authenticate=True, answer=True)
        db = self.model_to_dict(model, 'answer')
        url = reverse_lazy('feedback:answer_id',
                           kwargs={'answer_id': model['answer'].id})
        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': 'This survey does not exist for this user',
            'status_code': 404
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_with_data(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(authenticate=True,
                                     answer=True,
                                     user=True,
                                     answer_status='SENT')
        db = self.model_to_dict(model, 'answer')
        url = reverse_lazy('feedback:answer_id',
                           kwargs={'answer_id': model['answer'].id})
        response = self.client.get(url)
        json = response.json()

        del json["user"]
        self.assertEqual(
            json, {
                'id': model['answer'].id,
                'title': model['answer'].title,
                'lowest': model['answer'].lowest,
                'highest': model['answer'].highest,
                'lang': model['answer'].lang,
                'score': model['answer'].score,
                'comment': model['answer'].comment,
                'status': model['answer'].status,
                'opened_at': model['answer'].opened_at,
                'created_at': datetime_to_iso_format(
                    model['answer'].created_at),
                'updated_at': datetime_to_iso_format(
                    model['answer'].updated_at),
                'cohort': model['answer'].cohort,
                'academy': model['answer'].academy,
                'mentor': model['answer'].mentor,
                'event': model['answer'].event,
            })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_put_with_bad_id(self):
        """Test /answer/:id without auth"""
        self.generate_models(authenticate=True)
        url = reverse_lazy('feedback:answer_id', kwargs={'answer_id': 9999})
        response = self.client.put(url, {})
        json = response.json()
        expected = {
            'detail': 'This survey does not exist for this user',
            'status_code': 404,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_put_without_score(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(authenticate=True,
                                     answer=True,
                                     user=True,
                                     answer_status='SENT')
        db = self.model_to_dict(model, 'answer')
        data = {
            'comment': 'They killed kenny',
        }
        url = reverse_lazy('feedback:answer_id',
                           kwargs={'answer_id': model['answer'].id})
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(
            json, {'non_field_errors': ['Score must be between 1 and 10']})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_put_with_score_less_of_1(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(authenticate=True,
                                     answer=True,
                                     user=True,
                                     answer_status='SENT')
        db = self.model_to_dict(model, 'answer')
        url = reverse_lazy('feedback:answer_id',
                           kwargs={'answer_id': model['answer'].id})
        data = {
            'comment': 'They killed kenny',
            'score': 0,
        }
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(
            json, {'non_field_errors': ['Score must be between 1 and 10']})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_put_with_score_more_of_10(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(authenticate=True,
                                     answer=True,
                                     user=True,
                                     answer_status='SENT')
        db = self.model_to_dict(model, 'answer')
        url = reverse_lazy('feedback:answer_id',
                           kwargs={'answer_id': model['answer'].id})
        data = {
            'comment': 'They killed kenny',
            'score': 11,
        }
        response = self.client.put(url, data)
        json = response.json()

        self.assertEqual(
            json, {'non_field_errors': ['Score must be between 1 and 10']})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_answer_dict(), [db])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_put_with_all_valid_scores(self):
        """Test /answer/:id without auth"""
        for number in range(1, 10):
            self.remove_all_answer()
            model = self.generate_models(authenticate=True,
                                         answer=True,
                                         user=True,
                                         answer_status='SENT')
            db = self.model_to_dict(model, 'answer')
            url = reverse_lazy('feedback:answer_id',
                               kwargs={'answer_id': model['answer'].id})

            score = str(number)
            data = {
                'comment': 'They killed kenny',
                'score': score,
            }
            response = self.client.put(url, data)
            json = response.json()

            expected = {
                'id': model['answer'].id,
                'title': model['answer'].title,
                'lowest': model['answer'].lowest,
                'highest': model['answer'].highest,
                'lang': model['answer'].lang,
                'score': score,
                'comment': data['comment'],
                'status': 'ANSWERED',
                'opened_at': model['answer'].opened_at,
                'created_at':
                datetime_to_iso_format(model['answer'].created_at),
                'cohort': model['answer'].cohort,
                'academy': model['answer'].academy,
                'survey': None,
                'mentor': model['answer'].mentor,
                'event': model['answer'].event,
                'user': model['answer'].user.id,
            }

            del json['updated_at']

            self.assertEqual(json, expected)

            dicts = [
                answer for answer in self.all_answer_dict()
                if not 'updated_at' in answer
                or isinstance(answer['updated_at'], datetime)
                and answer.pop('updated_at')
            ]

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            db['score'] = score
            db['status'] = 'ANSWERED'
            db['comment'] = data['comment']

            self.assertEqual(dicts, [db])

    # TODO: this test should return 400 but its returning 200, why? If needs to return 400 because you cannot change your score in the answer once you already answered

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_answer_id_put_twice_different_score(self):
    #     """Test /answer/:id without auth"""
    #     model = self.generate_models(manual_authenticate=True, answer=True, user=True,answer_score=7,
    #         answer_status='SENT')
    #     db = self.model_to_dict(model, 'answer')
    #     url = reverse_lazy('feedback:answer_id', kwargs={'answer_id': model['answer'].id})
    #     data = {
    #         'comment': 'They killed kenny',
    #         'score': 1,
    #     }
    #     self.client.put(url, data)

    #     self.auth_with_token(model['user'])
    #     response = self.client.put(url, data)
    #     json = response.json()

    #     # assert False
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_answer_id_put_twice_same_score(self):
        """Test /answer/:id without auth"""
        model = self.generate_models(manual_authenticate=True,
                                     answer=True,
                                     user=True,
                                     answer_score=3,
                                     answer_status='SENT')
        db = self.model_to_dict(model, 'answer')
        url = reverse_lazy('feedback:answer_id',
                           kwargs={'answer_id': model['answer'].id})
        data = {
            'comment': 'They killed kenny',
            'score': '3',
        }
        self.client.put(url, data)

        self.auth_with_token(model['user'])
        response = self.client.put(url, data)
        json = response.json()

        # assert False
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        db['score'] = data['score']
        db['status'] = 'ANSWERED'
        db['comment'] = data['comment']

        self.assertEqual(self.all_answer_dict(), [db])

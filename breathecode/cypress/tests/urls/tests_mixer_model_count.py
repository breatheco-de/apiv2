import os
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import CypressTestCase


class AcademyEventTestSuite(CypressTestCase):
    def test_mixer_model__bad_environment__not_exits(self):
        if 'ALLOW_UNSAFE_CYPRESS_APP' in os.environ:
            del os.environ['ALLOW_UNSAFE_CYPRESS_APP']

        url = reverse_lazy('cypress:mixer_model_count',
                           kwargs={
                               'model_name': 'TheyKilledKenny',
                               'how_many': 1
                           })

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'is-not-allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mixer_model__bad_environment__empty_string(self):
        os.environ['ALLOW_UNSAFE_CYPRESS_APP'] = ''

        url = reverse_lazy('cypress:mixer_model_count',
                           kwargs={
                               'model_name': 'TheyKilledKenny',
                               'how_many': 1
                           })

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'is-not-allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mixer_model__without_data(self):
        os.environ['ALLOW_UNSAFE_CYPRESS_APP'] = 'True'
        url = reverse_lazy('cypress:mixer_model_count',
                           kwargs={
                               'model_name': 'TheyKilledKenny',
                               'how_many': 1
                           })

        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'is-empty', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mixer_model__bad_model_name(self):
        os.environ['ALLOW_UNSAFE_CYPRESS_APP'] = 'True'
        url = reverse_lazy('cypress:mixer_model_count',
                           kwargs={
                               'model_name': 'TheyKilledKenny',
                               'how_many': 1
                           })

        data = {'first_name': 'konan'}
        response = self.client.post(url, data)
        json = response.json()
        expected = [{
            'model': 'TheyKilledKenny',
            'pks': [],
            'index': 0,
            'status_text': 'Model not found'
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mixer_model__generate_one_profile_academy(self):
        os.environ['ALLOW_UNSAFE_CYPRESS_APP'] = 'True'
        url = reverse_lazy('cypress:mixer_model_count',
                           kwargs={
                               'model_name': 'ProfileAcademy',
                               'how_many': 1
                           })

        data = {'first_name': 'konan'}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = [{
            'index': 0,
            'model': 'ProfileAcademy',
            'pks': [1],
            'status_text': 'done',
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        all_profile_academy = self.all_profile_academy_dict()
        self.assertEqual(len(all_profile_academy), 1)
        self.assertEqual(all_profile_academy[0]['first_name'], 'konan')

    def test_mixer_model__generate_two_profile_academy(self):
        os.environ['ALLOW_UNSAFE_CYPRESS_APP'] = 'True'
        url = reverse_lazy('cypress:mixer_model_count',
                           kwargs={
                               'model_name': 'ProfileAcademy',
                               'how_many': 2
                           })

        data = {'first_name': 'konan'}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = [{
            'index': 0,
            'model': 'ProfileAcademy',
            'pks': [1, 2],
            'status_text': 'done',
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        all_profile_academy = self.all_profile_academy_dict()
        self.assertEqual(len(all_profile_academy), 2)
        self.assertEqual(all_profile_academy[0]['first_name'], 'konan')
        self.assertEqual(all_profile_academy[1]['first_name'], 'konan')

    def test_mixer_model__generate_one_user(self):
        os.environ['ALLOW_UNSAFE_CYPRESS_APP'] = 'True'
        url = reverse_lazy('cypress:mixer_model_count',
                           kwargs={
                               'model_name': 'User',
                               'how_many': 1
                           })

        data = {'first_name': 'konan'}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = [{
            'index': 0,
            'model': 'User',
            'pks': [1],
            'status_text': 'done',
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        all_user = self.all_user_dict()
        self.assertEqual(len(all_user), 1)
        self.assertEqual(all_user[0]['first_name'], 'konan')

    def test_mixer_model__generate_two_user(self):
        os.environ['ALLOW_UNSAFE_CYPRESS_APP'] = 'True'
        url = reverse_lazy('cypress:mixer_model_count',
                           kwargs={
                               'model_name': 'User',
                               'how_many': 2
                           })

        data = {'first_name': 'konan'}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = [{
            'index': 0,
            'model': 'User',
            'pks': [1, 2],
            'status_text': 'done',
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        all_user = self.all_user_dict()
        self.assertEqual(len(all_user), 2)
        self.assertEqual(all_user[0]['first_name'], 'konan')
        self.assertEqual(all_user[1]['first_name'], 'konan')

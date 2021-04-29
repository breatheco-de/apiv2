"""
Test /cohort/:id/user
"""
import re
from unittest.mock import patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins.new_admissions_test_case import AdmissionsTestCase

class CohortIdUserIdTestSuite(AdmissionsTestCase):
    """Test /cohort/:id/user"""

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_bad_cohort_id(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': 999})
        model = self.generate_models(authenticate=True)
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'Missing cohort_id or user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_bad_user(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': 999
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'invalid user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_without_user(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'Missing cohort_id or user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_without_profile_academy(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user':  model['user'].id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'Specified cohort not be found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        models_dict = self.all_cohort_user_dict()
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user':  model['user'].id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'id': 1,
            'role': 'STUDENT',
            'user': {
                'id': model['user'].id,
                'first_name': model['user'].first_name,
                'last_name': model['user'].last_name,
                'email': model['user'].email,
            },
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name,
                'never_ends': False,
                'kickoff_date': re.sub(
                    r'\+00:00$', 'Z',
                    model['cohort'].kickoff_date.isoformat()
                ),
                'current_day': model['cohort'].current_day,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'syllabus': None,
                'ending_date': model['cohort'].ending_date,
                'stage': model['cohort'].stage,
                'language': model['cohort'].language,
                'created_at': re.sub(r'\+00:00$', 'Z', model['cohort'].created_at.isoformat()),
                'updated_at': re.sub(r'\+00:00$', 'Z', model['cohort'].updated_at.isoformat()),
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cohort_user = self.get_cohort_user(1)
        cohort_user_two = cohort_user.__dict__.copy()
        cohort_user_two.update(data)
        cohort_user_two['user_id'] = cohort_user_two['user']
        cohort_user_two['cohort_id'] = model['cohort'].id
        del cohort_user_two['user']
        models_dict.append(self.remove_dinamics_fields(cohort_user_two))

        self.assertEqual(self.all_cohort_user_dict(), models_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_in_bulk_0_items(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = []
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.all_cohort_user_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_in_bulk_1_items(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = [{
            'user':  model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = [{
            'id': 1,
            'role': 'STUDENT',
            'user': {
                'id': model['user'].id,
                'first_name': model['user'].first_name,
                'last_name': model['user'].last_name,
                'email': model['user'].email,
            },
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name,
                'never_ends': False,
                'kickoff_date': re.sub(
                    r'\+00:00$', 'Z',
                    model['cohort'].kickoff_date.isoformat()
                ),
                'current_day': model['cohort'].current_day,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'syllabus': None,
                'ending_date': model['cohort'].ending_date,
                'stage': model['cohort'].stage,
                'language': model['cohort'].language,
                'created_at': re.sub(r'\+00:00$', 'Z', model['cohort'].created_at.isoformat()),
                'updated_at': re.sub(r'\+00:00$', 'Z', model['cohort'].updated_at.isoformat()),
            },
        }]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'STUDENT',
            'user_id': 1,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_in_bulk_2_items(self):
        """Test /cohort/:id/user without auth"""
        base = self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        del base['user']

        models = [self.generate_models(user=True, models=base) for _ in range(0, 2)]
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': models[0]['cohort'].id})
        data = [{
            'user':  model['user'].id,
        } for model in models]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = [{
            'id': model['user'].id - 1,
            'role': 'STUDENT',
            'user': {
                'id': model['user'].id,
                'first_name': model['user'].first_name,
                'last_name': model['user'].last_name,
                'email': model['user'].email,
            },
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name,
                'never_ends': False,
                'kickoff_date': re.sub(
                    r'\+00:00$', 'Z',
                    model['cohort'].kickoff_date.isoformat()
                ),
                'current_day': model['cohort'].current_day,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'syllabus': None,
                'ending_date': model['cohort'].ending_date,
                'stage': model['cohort'].stage,
                'language': model['cohort'].language,
                'created_at': re.sub(r'\+00:00$', 'Z', model['cohort'].created_at.isoformat()),
                'updated_at': re.sub(r'\+00:00$', 'Z', model['cohort'].updated_at.isoformat()),
            },
        } for model in models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'STUDENT',
            'user_id': 2,
        }, {
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 2,
            'role': 'STUDENT',
            'user_id': 3,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_two_cohort_with_the_same_certificate(self):
        """Test /cohort/:id/user without auth"""
        models = [self.generate_models(authenticate=True, cohort=True, user=True,
            profile_academy=True, cohort_user=True, syllabus=True, certificate=True)]

        base = models[0].copy()
        del base['user']
        del base['cohort']
        del base['cohort_user']

        models = models + [self.generate_models(cohort=True, user=True, cohort_user=True, models=base)]
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': models[1]['cohort'].id})
        data = {
            'user':  models[0]['user'].id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'status_code': 400,
            'detail': 'This student is already in another cohort for the same '
                'certificate, please mark him/her hi educational status on '
                'this prior cohort different than ACTIVE before cotinuing'
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_cohort_id_user_post_twice(self):
    #     """Test /cohort/:id/user without auth"""
    #     model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
    #     url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
    #     data = {
    #         'user':  model['user'].id,
    #     }
    #     self.client.post(url, data)
    #     response = self.client.post(url, data)
    #     json = response.json()
    #     expected = {'detail': 'That user already exists in this cohort', 'status_code': 400}

    #     self.assertEqual(json, expected)
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_one_teacher(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        models_dict = self.all_cohort_user_dict()
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user':  model['user'].id,
            'role': 'TEACHER'
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'id': 1,
            'role': 'TEACHER',
            'user': {
                'id': model['user'].id,
                'first_name': model['user'].first_name,
                'last_name': model['user'].last_name,
                'email': model['user'].email,
            },
            'cohort': {
                'id': model['cohort'].id,
                'slug': model['cohort'].slug,
                'name': model['cohort'].name,
                'never_ends': False,
                'kickoff_date': re.sub(
                    r'\+00:00$', 'Z',
                    model['cohort'].kickoff_date.isoformat()
                ),
                'current_day': model['cohort'].current_day,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'syllabus': None,
                'ending_date': model['cohort'].ending_date,
                'stage': model['cohort'].stage,
                'language': model['cohort'].language,
                'created_at': re.sub(r'\+00:00$', 'Z', model['cohort'].created_at.isoformat()),
                'updated_at': re.sub(r'\+00:00$', 'Z', model['cohort'].updated_at.isoformat()),
            },
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cohort_user = self.get_cohort_user(1)
        cohort_user_two = cohort_user.__dict__.copy()
        cohort_user_two.update(data)
        cohort_user_two['user_id'] = cohort_user_two['user']
        cohort_user_two['cohort_id'] = model['cohort'].id
        del cohort_user_two['user']
        models_dict.append(self.remove_dinamics_fields(cohort_user_two))

        self.assertEqual(self.all_cohort_user_dict(), models_dict)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_two_teacher(self):
        """Test /cohort/:id/user without auth"""
        models = [self.generate_models(authenticate=True, cohort=True, profile_academy=True)]

        base = models[0].copy()
        del base['user']

        models = models + [self.generate_models(user=True, models=base)]
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': models[0]['cohort'].id})
        data = {
            'user':  models[0]['user'].id,
            'role': 'TEACHER'
        }
        self.client.post(url, data)

        data = {
            'user':  models[1]['user'].id,
            'role': 'TEACHER'
        }
        response = self.client.post(url, data)
        json = response.json()

        # TODO: If you update the main teacher if should not give this error, only when you POST.
        expected = {
            'status_code': 400,
            'detail': 'There can only be one main instructor in a cohort',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_unsuccess_task(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True,
            task=True, task_status='PENDING', task_type='PROJECT')
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user':  model['user'].id,
            'educational_status': 'GRADUATED',
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'status_code': 400,
            'detail': 'User has tasks with status pending the educational status cannot be GRADUATED',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user_post_with_unsuccess_finantial_status(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user':  model['user'].id,
            'educational_status': 'GRADUATED',
            'finantial_status': 'LATE',
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'status_code': 400,
            'detail': 'Cannot be marked as `GRADUATED` if its financial status is `LATE`',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
from ..mixins import AdmissionsTestCase


class CohortIdUserIdTestSuite(AdmissionsTestCase):
    """Test /cohort/:id/user"""
    """
    🔽🔽🔽 Without cohord id in url
    """
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__with_bad_cohort_id(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': 999})
        model = self.generate_models(authenticate=True)
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'Missing cohort_id or user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Bad user in body
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__with_bad_user(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {'user': 999}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'invalid user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Without user in body
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__without_user(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {}
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'Missing cohort_id or user_id', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Authenticate user is not staff in this academy
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__without_profile_academy(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': model['user'].id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'Specified cohort not be found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    '''
    post to a cohort with stage DELETED
    '''

    def test_cohort_id_user__post__stage_deleted(self):
        """Test /cohort/:id/user without auth"""
        cohort_kwargs = {'stage': 'DELETED'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     cohort_kwargs=cohort_kwargs)
        models_dict = self.all_cohort_user_dict()
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': model['user'].id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'cohort-with-stage-deleted', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.all_cohort_user_dict(), [])

    """
    🔽🔽🔽 Post
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        models_dict = self.all_cohort_user_dict()
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': model['user'].id,
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
                'remote_available': True,
                'kickoff_date': re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
                'current_day': model['cohort'].current_day,
                'online_meeting_url': model['cohort'].online_meeting_url,
                'timezone': model['cohort'].timezone,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'schedule': None,
                'syllabus_version': None,
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

    """
    🔽🔽🔽 Post in bulk mode
    """

    def test_cohort_id_user__post__in_bulk__cohort_with_stage_deleted(self):
        """Test /cohort/:id/user without auth"""
        cohort_kwargs = {'stage': 'DELETED'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     cohort_kwargs=cohort_kwargs)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = [{
            'user': model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'cohort-with-stage-deleted', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__in_bulk__zero_items(self):
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
    def test_cohort_id_user__post__in_bulk__with_one_item(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = [{
            'user': model['user'].id,
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
                'remote_available': True,
                'kickoff_date': re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
                'current_day': model['cohort'].current_day,
                'online_meeting_url': model['cohort'].online_meeting_url,
                'timezone': model['cohort'].timezone,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'schedule': None,
                'syllabus_version': None,
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
    def test_cohort_id_user__post__in_bulk__with_two_items(self):
        """Test /cohort/:id/user without auth"""
        base = self.generate_models(authenticate=True, cohort=True, profile_academy=True)
        del base['user']

        models = [self.generate_models(user=True, models=base) for _ in range(0, 2)]
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': models[0]['cohort'].id})
        data = [{
            'user': model['user'].id,
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
                'remote_available': True,
                'kickoff_date': re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
                'current_day': model['cohort'].current_day,
                'online_meeting_url': model['cohort'].online_meeting_url,
                'timezone': model['cohort'].timezone,
                'academy': {
                    'id': model['cohort'].academy.id,
                    'name': model['cohort'].academy.name,
                    'slug': model['cohort'].academy.slug,
                    'country': model['cohort'].academy.country.code,
                    'city': model['cohort'].academy.city.id,
                    'street_address': model['cohort'].academy.street_address,
                },
                'schedule': None,
                'syllabus_version': None,
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

    """
    🔽🔽🔽 User in two cohort with the same certificate
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__with_two_cohort__with_the_same_certificate(self):
        """Test /cohort/:id/user without auth"""
        models = [
            self.generate_models(authenticate=True,
                                 cohort=True,
                                 user=True,
                                 profile_academy=True,
                                 cohort_user=True,
                                 syllabus=True,
                                 syllabus_schedule=True)
        ]

        base = models[0].copy()
        del base['user']
        del base['cohort']
        del base['cohort_user']

        models = models + [self.generate_models(cohort=True, user=True, cohort_user=True, models=base)]
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': models[1]['cohort'].id})
        data = {
            'user': models[0]['user'].id,
        }
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'status_code':
            400,
            'detail': ('This student is already in another cohort for the same '
                       'certificate, please mark him/her hi educational status on '
                       'this prior cohort different than ACTIVE before cotinuing')
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Post adding the same user twice
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__twice(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     cohort_user=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': model['user'].id,
        }
        # self.client.post(url, data)
        response = self.client.post(url, data)
        json = response.json()
        expected = {'detail': 'That user already exists in this cohort', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Post one teacher
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__role_student(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     role='student')
        models_dict = self.all_cohort_user_dict()
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {'user': model['user'].id, 'role': 'TEACHER'}
        response = self.client.post(url, data)
        json = response.json()
        expected = {
            'detail': 'The user must be staff member to this academy before it can be a teacher',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_staff(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('staff')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_teacher(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('teacher')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_syllabus_coordinator(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('syllabus_coordinator')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_homework_reviewer(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('homework_reviewer')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_growth_manager(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('growth_manager')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_culture_and_recruitment(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('culture_and_recruitment')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_country_manager(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('country_manager')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_community_manager(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('community_manager')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_career_support(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('career_support')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_assistant(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('assistant')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_admissions_developer(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('admissions_developer')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_admin(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('admin')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_academy_token(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('academy_token')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__one_teacher__with_role_academy_coordinator(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('academy_coordinator')

    """
    🔽🔽🔽 Post just one main teacher for cohort
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__two_teacher(self):
        """Test /cohort/:id/user without auth"""
        models = [self.generate_models(authenticate=True, cohort=True, profile_academy=True, role='staff')]

        base = models[0].copy()
        del base['user']
        del base['profile_academy']

        models = models + [self.generate_models(user=True, models=base, profile_academy=True)]
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': models[0]['cohort'].id})
        data = {'user': models[0]['user'].id, 'role': 'TEACHER'}
        self.client.post(url, data)

        data = {'user': models[1]['user'].id, 'role': 'TEACHER'}
        response = self.client.post(url, data)
        json = response.json()

        expected = {
            'status_code': 400,
            'detail': 'There can only be one main instructor in a cohort',
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    🔽🔽🔽 Student cannot be graduated if has pending tasks
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__with_unsuccess_task(self):
        """Test /cohort/:id/user without auth"""
        task = {'task_status': 'PENDING', 'task_type': 'PROJECT'}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     task=task)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': model['user'].id,
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

    """
    🔽🔽🔽 Student cannot graduated if its financial status is late
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__with_unsuccess_finantial_status(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True, cohort=True, user=True, profile_academy=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': model['user'].id,
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

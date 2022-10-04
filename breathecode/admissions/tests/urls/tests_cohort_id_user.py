"""
Test /cohort/:id/user
"""
import random
import re
from django.utils import timezone
from unittest.mock import MagicMock, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ..mixins import AdmissionsTestCase

UTC_NOW = timezone.now()


def post_serializer(self, cohort, user, profile_academy=None, data={}):
    return {
        'cohort': {
            'ending_date': cohort.ending_date,
            'id': cohort.id,
            'kickoff_date': self.bc.datetime.to_iso_string(cohort.kickoff_date),
            'name': cohort.name,
            'slug': cohort.slug,
            'stage': cohort.stage,
        },
        'created_at': self.bc.datetime.to_iso_string(UTC_NOW),
        'educational_status': None,
        'finantial_status': None,
        'id': 1,
        'profile_academy': {
            'email': profile_academy.email,
            'first_name': profile_academy.first_name,
            'id': profile_academy.id,
            'last_name': profile_academy.last_name,
            'phone': profile_academy.phone,
        } if profile_academy else None,
        'role': 'STUDENT',
        'user': {
            'email': user.email,
            'first_name': user.first_name,
            'id': user.id,
            'last_name': user.last_name,
        },
        'watching': False,
        **data,
    }


def cohort_user_field(data={}):
    return {
        'cohort_id': 0,
        'educational_status': None,
        'finantial_status': None,
        'id': 0,
        'role': 'STUDENT',
        'user_id': 0,
        'watching': False,
        **data,
    }


def check_cohort_user_that_not_have_role_student_can_be_teacher(self, role, update=False, additional_data={}):
    """Test /cohort/:id/user without auth"""
    self.headers(academy=1)

    model_kwargs = {
        'authenticate': True,
        'cohort': {
            'stage': 'STARTED'
        },
        'user': True,
        'profile_academy': True,
        'role': role,
        'capability': 'crud_cohort',
    }

    if update:
        model_kwargs['cohort_user'] = True

    model = self.generate_models(**model_kwargs)

    url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': 1})
    data = {'user': model['user'].id, 'role': 'TEACHER'}

    request_func = self.client.put if update else self.client.post
    response = request_func(url, data, format='json')

    json = response.json()
    expected = post_serializer(self,
                               model.cohort,
                               model.user,
                               model.profile_academy,
                               data={
                                   'role': 'TEACHER',
                                   **additional_data,
                               })

    expected['educational_status'] = None
    expected['finantial_status'] = None

    self.assertEqual(json, expected)

    if update:
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    else:
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    if update:
        self.assertEqual(self.all_cohort_user_dict(),
                         [{
                             **self.model_to_dict(model, 'cohort_user'),
                             'role': 'TEACHER',
                         }])
    else:
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'TEACHER',
            'user_id': 1,
            'watching': False,
        }])


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
        response = self.client.post(url, data, format='json')
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
        response = self.client.post(url, data, format='json')
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
        response = self.client.post(url, data, format='json')
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
        model = self.generate_models(authenticate=True, user=True, cohort=1)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': model['user'].id,
        }
        response = self.client.post(url, data, format='json')
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
        models_dict = self.bc.database.list_of('admissions.CohortUser')
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': model['user'].id,
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'adding-student-to-a-closed-cohort', 'status_code': 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    """
    🔽🔽🔽 Post
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort={'stage': 'STARTED'},
                                     user=True,
                                     profile_academy=True)
        models_dict = self.bc.database.list_of('admissions.CohortUser')
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': model['user'].id,
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = post_serializer(self, model.cohort, model.user, model.profile_academy, data={})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cohort_user = self.get_cohort_user(1)
        cohort_user_two = cohort_user.__dict__.copy()
        cohort_user_two.update(data)
        cohort_user_two['user_id'] = cohort_user_two['user']
        cohort_user_two['cohort_id'] = model['cohort'].id
        del cohort_user_two['user']
        models_dict.append(self.remove_dinamics_fields(cohort_user_two))

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), models_dict)

    """
    🔽🔽🔽 Post
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__status_in_upper_and_lower(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort={'stage': 'STARTED'},
                                     user=True,
                                     profile_academy=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model.cohort.id})

        roles = ['TEACHER', 'ASSISTANT', 'STUDENT', 'REVIEWER']
        finantial_status = ['FULLY_PAID', 'UP_TO_DATE', 'LATE']
        educational_status = ['ACTIVE', 'POSTPONED', 'SUSPENDED', 'DROPPED']  # do not put GRADUATED here
        data = {
            'user': model['user'].id,
            'role': random.choice(roles + [x.lower() for x in roles]),
            'finantial_status': random.choice(finantial_status + [x.lower() for x in finantial_status]),
            'educational_status': random.choice(educational_status + [x.lower() for x in educational_status]),
        }

        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = post_serializer(self,
                                   model.cohort,
                                   model.user,
                                   model.profile_academy,
                                   data={
                                       'role': data['role'].upper(),
                                       'finantial_status': data['finantial_status'].upper(),
                                       'educational_status': data['educational_status'].upper(),
                                   })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            cohort_user_field({
                'id': 1,
                'cohort_id': 1,
                'user_id': 1,
                'role': data['role'].upper(),
                'finantial_status': data['finantial_status'].upper(),
                'educational_status': data['educational_status'].upper(),
            }),
        ])

    """
    🔽🔽🔽 Post in bulk mode
    """

    def test_cohort_id_user__post__in_bulk__cohort_with_stage_deleted(self):
        """Test /cohort/:id/user without auth"""

        model = self.generate_models(
            authenticate=True,
            cohort={'stage': 'DELETED'},
            user=True,
            profile_academy=True,
        )
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = [{
            'user': model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'adding-student-to-a-closed-cohort', 'status_code': 400}
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

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
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__in_bulk__with_one_item(self):
        """Test /cohort/:id/user without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort={'stage': 'STARTED'},
                                     user=True,
                                     profile_academy=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = [{
            'user': model['user'].id,
        }]
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = [
            post_serializer(self, model.cohort, model.user, model.profile_academy, data={
                'role': 'STUDENT',
            })
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'STUDENT',
            'user_id': 1,
            'watching': False,
        }])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__in_bulk__with_two_items(self):
        """Test /cohort/:id/user without auth"""
        base = self.generate_models(authenticate=True, cohort={'stage': 'STARTED'}, profile_academy=True)
        del base['user']

        models = [self.generate_models(user=True, models=base) for _ in range(0, 2)]
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': models[0]['cohort'].id})
        data = [{
            'user': model['user'].id,
        } for model in models]
        response = self.client.post(url, data, format='json')
        json = response.json()

        expected = [
            post_serializer(self,
                            model.cohort,
                            model.user,
                            None,
                            data={
                                'id': model.user.id - 1,
                                'role': 'STUDENT',
                            }) for model in models
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'STUDENT',
            'user_id': 2,
            'watching': False
        }, {
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 2,
            'role': 'STUDENT',
            'user_id': 3,
            'watching': False
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
                                 cohort={'stage': 'STARTED'},
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

        models = models + [
            self.generate_models(cohort={'stage': 'STARTED'}, user=True, cohort_user=True, models=base)
        ]
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': models[1]['cohort'].id})
        data = {
            'user': models[0]['user'].id,
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': ('This student is already in another cohort for the same '
                       'certificate, please mark him/her hi educational status on '
                       'this prior cohort different than ACTIVE before cotinuing'),
            'status_code':
            400
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
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {'detail': 'adding-student-to-a-closed-cohort', 'status_code': 400}

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
                                     cohort={'stage': 'STARTED'},
                                     user=True,
                                     profile_academy=True,
                                     role='student')
        models_dict = self.bc.database.list_of('admissions.CohortUser')
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {'user': model['user'].id, 'role': 'TEACHER'}
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'The user must be staff member to this academy before it can be a teacher',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_staff(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'staff')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_teacher(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'teacher')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_syllabus_coordinator(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'syllabus_coordinator')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_homework_reviewer(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'homework_reviewer')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_growth_manager(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'growth_manager')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_culture_and_recruitment(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'culture_and_recruitment')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_country_manager(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'country_manager')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_community_manager(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'community_manager')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_career_support(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'career_support')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_assistant(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'assistant')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_admissions_developer(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'admissions_developer')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_admin(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'admin')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_academy_token(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'academy_token')

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_cohort_id_user__post__one_teacher__with_role_academy_coordinator(self):
        """Test /cohort/:id/user without auth"""
        check_cohort_user_that_not_have_role_student_can_be_teacher(self, 'academy_coordinator')

    """
    🔽🔽🔽 Post just one main teacher for cohort
    """

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_cohort_id_user__post__two_teacher(self):
        """Test /cohort/:id/user without auth"""
        models = [
            self.generate_models(authenticate=True,
                                 cohort={'stage': 'STARTED'},
                                 profile_academy=True,
                                 role='staff')
        ]

        base = models[0].copy()
        del base['user']
        del base['profile_academy']

        models = models + [self.generate_models(user=True, models=base, profile_academy=True)]
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': models[0]['cohort'].id})
        data = {'user': models[0]['user'].id, 'role': 'TEACHER'}
        self.client.post(url, data, format='json')

        data = {'user': models[1]['user'].id, 'role': 'TEACHER'}
        response = self.client.post(url, data, format='json')
        json = response.json()

        expected = {'detail': 'There can only be one main instructor in a cohort', 'status_code': 400}
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
        task = {'task_status': 'PENDING', 'task_type': 'PROJECT', 'associated_slug': 'testing-slug'}
        model = self.generate_models(authenticate=True,
                                     cohort={'stage': 'STARTED'},
                                     user=True,
                                     profile_academy=True,
                                     task=task,
                                     syllabus_version={
                                         'id': 1,
                                         'json': {
                                             'days': [{
                                                 'assignments': [{
                                                     'slug': 'testing-slug',
                                                 }]
                                             }]
                                         }
                                     })
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': model['user'].id,
            'educational_status': 'GRADUATED',
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'User has tasks with status pending the educational status cannot be GRADUATED',
            'status_code': 400
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
        model = self.generate_models(authenticate=True,
                                     cohort={'stage': 'STARTED'},
                                     user=True,
                                     profile_academy=True)
        url = reverse_lazy('admissions:cohort_id_user', kwargs={'cohort_id': model['cohort'].id})
        data = {
            'user': model['user'].id,
            'educational_status': 'GRADUATED',
            'finantial_status': 'LATE',
        }
        response = self.client.post(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'Cannot be marked as `GRADUATED` if its financial status is `LATE`',
            'status_code': 400
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

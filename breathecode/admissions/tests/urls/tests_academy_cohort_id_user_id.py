"""
Test /cohort/:id/user/:id
"""
import re
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import AdmissionsTestCase


class CohortUserTestSuite(AdmissionsTestCase):
    """Test /cohort/user"""
    """
    🔽🔽🔽 Auth
    """
    def test_academy_cohort_user__without_auth(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        response = self.client.post(url, {})
        json = response.json()

        self.assertEqual(
            json, {
                'detail': 'Authentication credentials were not provided.',
                'status_code': status.HTTP_401_UNAUTHORIZED
            })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    """
    🔽🔽🔽 Post method
    """

    def test_academy_cohort_user__post(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')

        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        data = {
            'user': model['user'].id,
            'cohort': model['cohort'].id,
        }
        response = self.client.post(url, data, format='json')
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
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'STUDENT',
            'user_id': 1,
        }])

    """
    🔽🔽🔽 Add the same teacher to two cohors
    """

    def test_academy_cohort_user__post__same_teacher_in_two_cohorts(self):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)
        models = [
            self.generate_models(authenticate=True,
                                 user=True,
                                 cohort=True,
                                 profile_academy=True,
                                 capability='crud_cohort',
                                 role='staff')
        ]

        base = models[0].copy()
        del base['cohort']

        models = models + [self.generate_models(cohort=True, models=base)]
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        data = {
            'user': 1,
            'cohort': 1,
            'role': 'TEACHER',
        }
        response = self.client.post(url, data, format='json')

        data = {
            'user': 1,
            'cohort': 2,
            'role': 'TEACHER',
        }
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 2, 'user_id': 1})
        response = self.client.post(url, data, format='json')
        json = response.json()
        model = models[1]
        expected = {
            'id': 2,
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
        self.assertEqual(self.all_cohort_user_dict(), [{
            'cohort_id': 1,
            'educational_status': None,
            'finantial_status': None,
            'id': 1,
            'role': 'TEACHER',
            'user_id': 1,
        }, {
            'cohort_id': 2,
            'educational_status': None,
            'finantial_status': None,
            'id': 2,
            'role': 'TEACHER',
            'user_id': 1,
        }])

    """
    🔽🔽🔽 Put
    """

    def test_academy_cohort_user__put(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='potato')
        data = {
            'id': model['cohort_user'].id,
            'user': 1,
            'cohort': 1,
        }
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'id': 1,
            'role': 'STUDENT',
            'educational_status': None,
            'finantial_status': None,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_user_dict(),
                         [{
                             **self.model_to_dict(model, 'cohort_user'),
                             'role': 'STUDENT',
                         }])

    """
    🔽🔽🔽 Put teacher
    """

    def test_academy_cohort_user__put__teacher_with_role_student(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='student')
        data = {
            'id': model['cohort_user'].id,
            'role': 'TEACHER',
            'user': 1,
            'cohort': 1,
        }
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {
            'detail': 'The user must be staff member to this academy before it can be a teacher',
            'status_code': 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_cohort_user_dict(),
                         [{
                             **self.model_to_dict(model, 'cohort_user'),
                             'role': 'STUDENT',
                         }])

    def test_academy_cohort_user__put__teacher(self):
        """Test /cohort/user without auth"""
        self.headers(academy=1)
        url = reverse_lazy('admissions:academy_cohort_id_user_id', kwargs={'cohort_id': 1, 'user_id': 1})
        model = self.generate_models(authenticate=True,
                                     cohort_user=True,
                                     profile_academy=True,
                                     capability='crud_cohort',
                                     role='staff')
        data = {
            'id': model['cohort_user'].id,
            'role': 'TEACHER',
            'user': 1,
            'cohort': 1,
        }
        response = self.client.put(url, data, format='json')
        json = response.json()
        expected = {'id': 1, 'role': 'TEACHER', 'educational_status': None, 'finantial_status': None}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_user_dict(),
                         [{
                             **self.model_to_dict(model, 'cohort_user'),
                             'role': 'TEACHER',
                         }])

    def test_academy_cohort_id_user__post__one_teacher__with_role_staff(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('staff', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_teacher(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('teacher', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_syllabus_coordinator(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('syllabus_coordinator', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_homework_reviewer(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('homework_reviewer', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_growth_manager(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('growth_manager', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_culture_and_recruitment(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('culture_and_recruitment',
                                                                         update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_country_manager(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('country_manager', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_community_manager(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('community_manager', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_career_support(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('career_support', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_assistant(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('assistant', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_admissions_developer(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('admissions_developer', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_admin(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('admin', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_academy_token(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('academy_token', update=True)

    def test_academy_cohort_id_user__post__one_teacher__with_role_academy_coordinator(self):
        """Test /cohort/:id/user without auth"""
        self.check_cohort_user_that_not_have_role_student_can_be_teacher('academy_coordinator', update=True)

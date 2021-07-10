"""
Collections of mixins used to login in authorize microservice
"""
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase
from breathecode.tests.mixins import GenerateModelsMixin, CacheMixin, GenerateQueriesMixin, DatetimeMixin, ICallMixin
from rest_framework import status


class AdmissionsTestCase(APITestCase, GenerateModelsMixin, CacheMixin,
                         GenerateQueriesMixin, DatetimeMixin, ICallMixin):
    """AdmissionsTestCase with auth methods"""
    def setUp(self):
        self.generate_queries()

    def tearDown(self):
        self.clear_cache()

    def fill_cohort_timeslot(self, id, cohort_id, certificate_timeslot):
        return {
            'id': id,
            'cohort_id': cohort_id,
            'starting_at': certificate_timeslot.starting_at,
            'ending_at': certificate_timeslot.ending_at,
            'recurrent': certificate_timeslot.recurrent,
            'recurrency_type': certificate_timeslot.recurrency_type,
        }

    def check_cohort_user_that_not_have_role_student_can_be_teacher(
            self, role, update=False):
        """Test /cohort/:id/user without auth"""
        self.headers(academy=1)

        model_kwargs = {
            'authenticate': True,
            'cohort': True,
            'user': True,
            'profile_academy': True,
            'role': role,
            'capability': 'crud_cohort',
        }

        if update:
            model_kwargs['cohort_user'] = True

        model = self.generate_models(**model_kwargs)

        reverse_name = 'academy_cohort_id_user_id' if update else 'cohort_id_user'
        url_params = {
            'cohort_id': 1,
            'user_id': 1
        } if update else {
            'cohort_id': 1
        }
        url = reverse_lazy(f'admissions:{reverse_name}', kwargs=url_params)
        data = {'user': model['user'].id, 'role': 'TEACHER'}

        request_func = self.client.put if update else self.client.post
        response = request_func(url, data)
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
                'kickoff_date':
                self.datetime_to_iso(model['cohort'].kickoff_date),
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
                'created_at': self.datetime_to_iso(model['cohort'].created_at),
                'updated_at': self.datetime_to_iso(model['cohort'].updated_at),
            },
        }

        if update:
            del expected['user']
            del expected['cohort']

            expected['educational_status'] = None
            expected['finantial_status'] = None

        self.assertEqual(json, expected)

        if update:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        else:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        if update:
            self.assertEqual(
                self.all_cohort_user_dict(),
                [{
                    **self.model_to_dict(model, 'cohort_user'),
                    'role': 'TEACHER',
                }])
        else:
            self.assertEqual(self.all_cohort_user_dict(),
                             [{
                                 'cohort_id': 1,
                                 'educational_status': None,
                                 'finantial_status': None,
                                 'id': 1,
                                 'role': 'TEACHER',
                                 'user_id': 1
                             }])

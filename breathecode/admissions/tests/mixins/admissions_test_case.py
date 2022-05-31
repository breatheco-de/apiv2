"""
Collections of mixins used to login in authorize microservice
"""
import re
from unittest.mock import MagicMock, patch
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase
from breathecode.tests.mixins import (GenerateModelsMixin, CacheMixin, GenerateQueriesMixin, DatetimeMixin,
                                      ICallMixin, BreathecodeMixin)
from rest_framework import status


class AdmissionsTestCase(APITestCase, GenerateModelsMixin, CacheMixin, GenerateQueriesMixin, DatetimeMixin,
                         ICallMixin, BreathecodeMixin):
    """AdmissionsTestCase with auth methods"""
    def setUp(self):
        self.generate_queries()
        self.set_test_instance(self)

    def tearDown(self):
        self.clear_cache()

    def fill_cohort_timeslot(self, id, cohort_id, certificate_timeslot, timezone='America/New_York'):
        return {
            'id': id,
            'cohort_id': cohort_id,
            'starting_at': certificate_timeslot.starting_at,
            'ending_at': certificate_timeslot.ending_at,
            'recurrent': certificate_timeslot.recurrent,
            'recurrency_type': certificate_timeslot.recurrency_type,
            'timezone': timezone,
        }

    def check_cohort_user_that_not_have_role_student_can_be_teacher(self, role, update=False):
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
        url_params = {'cohort_id': 1, 'user_id': 1} if update else {'cohort_id': 1}
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
                'remote_available': True,
                'kickoff_date': self.datetime_to_iso(model['cohort'].kickoff_date),
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
                'user_id': 1
            }])

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def check_academy_cohort__with_data(self, models=None, deleted=False):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)

        cohort_time_slots = self.all_cohort_time_slot_dict()
        if cohort_time_slots:
            cohort_time_slot = cohort_time_slots[0]

        if models is None:
            syllabus_kwargs = {'slug': 'they-killed-kenny'}
            academy_kwargs = {'timezone': 'America/Caracas'}
            models = [
                self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato',
                                     syllabus=True,
                                     syllabus_version=True,
                                     syllabus_schedule=True,
                                     syllabus_schedule_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs,
                                     academy_kwargs=academy_kwargs)
            ]

            # reset because this call are coming from mixer
            cohort_saved.send.call_args_list = []

        models.sort(key=lambda x: x.cohort.kickoff_date, reverse=True)

        url = reverse_lazy('admissions:academy_cohort')
        response = self.client.get(url)
        json = response.json()

        if deleted:
            expected = []

        else:
            expected = [{
                'id':
                model['cohort'].id,
                'slug':
                model['cohort'].slug,
                'name':
                model['cohort'].name,
                'never_ends':
                model['cohort'].never_ends,
                'remote_available':
                model['cohort'].remote_available,
                'private':
                model['cohort'].private,
                'kickoff_date':
                re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
                'ending_date':
                model['cohort'].ending_date,
                'stage':
                model['cohort'].stage,
                'language':
                model['cohort'].language,
                'current_day':
                model['cohort'].current_day,
                'current_module':
                model['cohort'].current_module,
                'online_meeting_url':
                model['cohort'].online_meeting_url,
                'timezone':
                model['cohort'].timezone,
                'timeslots': [{
                    'ending_at':
                    self.interger_to_iso(cohort_time_slot['timezone'], cohort_time_slot['ending_at']),
                    'id':
                    cohort_time_slot['id'],
                    'recurrency_type':
                    cohort_time_slot['recurrency_type'],
                    'recurrent':
                    cohort_time_slot['recurrent'],
                    'starting_at':
                    self.interger_to_iso(cohort_time_slot['timezone'], cohort_time_slot['starting_at']),
                }] if cohort_time_slots and model.cohort.id != 1 else [],
                'schedule': {
                    'id': model['cohort'].schedule.id,
                    'name': model['cohort'].schedule.name,
                    'syllabus': model['cohort'].schedule.syllabus.id,
                },
                'syllabus_version': {
                    'name': model.syllabus.name,
                    'slug': model.syllabus.slug,
                    'status': model['cohort'].syllabus_version.status,
                    'version': model['cohort'].syllabus_version.version,
                    'syllabus': model['cohort'].syllabus_version.syllabus.id,
                    'duration_in_days': model.syllabus.duration_in_days,
                    'duration_in_hours': model.syllabus.duration_in_hours,
                    'github_url': model.syllabus.github_url,
                    'logo': model.syllabus.logo,
                    'private': model.syllabus.private,
                    'week_hours': model.syllabus.week_hours,
                },
                'academy': {
                    'id': model['cohort'].academy.id,
                    'slug': model['cohort'].academy.slug,
                    'name': model['cohort'].academy.name,
                    'country': {
                        'code': model['cohort'].academy.country.code,
                        'name': model['cohort'].academy.country.name,
                    },
                    'city': {
                        'name': model['cohort'].academy.city.name,
                    },
                    'logo_url': model['cohort'].academy.logo_url,
                },
            } for model in models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict([x.cohort for x in models]))
        self.assertEqual(cohort_saved.send.call_args_list, [])
        return models

    @patch('breathecode.admissions.signals.cohort_saved.send', MagicMock())
    def check_cohort_me__with_data(self, models=None, deleted=False):
        """Test /cohort without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)

        cohort_time_slots = self.all_cohort_time_slot_dict()
        if cohort_time_slots:
            cohort_time_slot = cohort_time_slots[0]

        if models is None:
            syllabus_kwargs = {'slug': 'they-killed-kenny'}
            academy_kwargs = {'timezone': 'America/Caracas'}
            models = [
                self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     capability='read_all_cohort',
                                     role='potato',
                                     syllabus=True,
                                     cohort_user=1,
                                     syllabus_version=True,
                                     syllabus_schedule=True,
                                     syllabus_schedule_time_slot=True,
                                     syllabus_kwargs=syllabus_kwargs,
                                     academy_kwargs=academy_kwargs)
            ]

            # reset because this call are coming from mixer
            cohort_saved.send.call_args_list = []

        models.sort(key=lambda x: x.cohort.kickoff_date, reverse=True)

        url = reverse_lazy('admissions:academy_cohort')
        response = self.client.get(url)
        json = response.json()

        if deleted:
            expected = []

        else:
            expected = [{
                'id':
                model['cohort'].id,
                'slug':
                model['cohort'].slug,
                'name':
                model['cohort'].name,
                'never_ends':
                model['cohort'].never_ends,
                'remote_available':
                model['cohort'].remote_available,
                'private':
                model['cohort'].private,
                'kickoff_date':
                re.sub(r'\+00:00$', 'Z', model['cohort'].kickoff_date.isoformat()),
                'ending_date':
                model['cohort'].ending_date,
                'stage':
                model['cohort'].stage,
                'language':
                model['cohort'].language,
                'current_day':
                model['cohort'].current_day,
                'current_module':
                model['cohort'].current_module,
                'online_meeting_url':
                model['cohort'].online_meeting_url,
                'timezone':
                model['cohort'].timezone,
                'timeslots': [{
                    'ending_at':
                    self.interger_to_iso(cohort_time_slot['timezone'], cohort_time_slot['ending_at']),
                    'id':
                    cohort_time_slot['id'],
                    'recurrency_type':
                    cohort_time_slot['recurrency_type'],
                    'recurrent':
                    cohort_time_slot['recurrent'],
                    'starting_at':
                    self.interger_to_iso(cohort_time_slot['timezone'], cohort_time_slot['starting_at']),
                }] if cohort_time_slots and model.cohort.id != 1 else [],
                'schedule': {
                    'id': model['cohort'].schedule.id,
                    'name': model['cohort'].schedule.name,
                    'syllabus': model['cohort'].schedule.syllabus.id,
                },
                'syllabus_version': {
                    'name': model.syllabus.name,
                    'slug': model.syllabus.slug,
                    'status': model['cohort'].syllabus_version.status,
                    'version': model['cohort'].syllabus_version.version,
                    'syllabus': model['cohort'].syllabus_version.syllabus.id,
                    'duration_in_days': model.syllabus.duration_in_days,
                    'duration_in_hours': model.syllabus.duration_in_hours,
                    'github_url': model.syllabus.github_url,
                    'logo': model.syllabus.logo,
                    'private': model.syllabus.private,
                    'week_hours': model.syllabus.week_hours,
                },
                'academy': {
                    'id': model['cohort'].academy.id,
                    'slug': model['cohort'].academy.slug,
                    'name': model['cohort'].academy.name,
                    'country': {
                        'code': model['cohort'].academy.country.code,
                        'name': model['cohort'].academy.country.name,
                    },
                    'city': {
                        'name': model['cohort'].academy.city.name,
                    },
                    'logo_url': model['cohort'].academy.logo_url,
                },
            } for model in models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_cohort_dict(), self.all_model_dict([x.cohort for x in models]))
        self.assertEqual(cohort_saved.send.call_args_list, [])
        return models
